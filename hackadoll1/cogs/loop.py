import asyncio
import time
from contextlib import suppress
from datetime import datetime
from html import unescape

import pytz
import requests
import hkdhelper as hkd
from bs4 import BeautifulSoup
from dateutil import parser
from discord import Colour
from discord.ext import commands, tasks

class Loop(commands.Cog):
    def __init__(self, bot, config, firebase_ref, calendar, twitter_api):
        self.bot = bot
        self.config = config
        self.firebase_ref = firebase_ref
        self.calendar = calendar
        self.twitter_api = twitter_api
        self.check_tweets.start()
        self.check_live_streams.start()

    @tasks.loop(seconds=30.0)
    async def check_tweets(self):
        channel = hkd.get_updates_channel(self.bot.guilds)
        with suppress(Exception):
            twitter_user_ids = self.firebase_ref.child('last_userid_tweets').get().keys()
            for user_id_str in twitter_user_ids:
                user_id = int(user_id_str)
                last_tweet_id = int(self.firebase_ref.child('last_userid_tweets/{0}'.format(user_id)).get())
                posted_tweets = []
                tweets = self.twitter_api.GetUserTimeline(user_id=user_id, since_id=last_tweet_id, count=40, include_rts=False)
                for tweet in reversed(tweets):
                    user = tweet.user
                    name = user.name
                    username = user.screen_name
                    if tweet.in_reply_to_user_id and str(tweet.in_reply_to_user_id) not in twitter_user_ids:
                        continue
                    await asyncio.sleep(0.5)
                    tweet_id = tweet.id
                    posted_tweets.append(tweet_id)
                    tweet_content = unescape(tweet.full_text)
                    if user_id in hkd.WUG_TWITTER_IDS.values():
                        colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), hkd.dict_reverse(hkd.WUG_TWITTER_IDS)[user_id])
                    else:
                        colour = Colour(0x242424)
                    author = {}
                    author['name'] = '{0} (@{1})'.format(name, username)
                    author['url'] = 'https://twitter.com/{0}'.format(username)
                    author['icon_url'] = user.profile_image_url_https
                    image = ''
                    if (expanded_urls := tweet.urls) and (expanded_url := expanded_urls[0].expanded_url) and hkd.is_blog_post(expanded_url):
                        soup = hkd.get_html_from_url(expanded_url)
                        blog_entry = soup.find(attrs={'class': 'skin-entryBody'})
                        if blog_images := [p['src'] for p in blog_entry.find_all('img') if '?caw=' in p['src'][-9:]]:
                            image = blog_images[0]
                    if media := tweet.media:
                        image = media[0].media_url_https
                    await channel.send(embed=hkd.create_embed(author=author, title='Tweet by {0}'.format(name), description=tweet_content, colour=colour, url='https://twitter.com/{0}/status/{1}'.format(username, tweet_id), image=image))
                if posted_tweets:
                    self.firebase_ref.child('last_userid_tweets/{0}'.format(user_id)).set(str(max(posted_tweets)))

    @check_tweets.before_loop
    async def before_check_tweets(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30.0)
    async def check_live_streams(self):
        channel = hkd.get_seiyuu_channel(self.bot.guilds)
        now = datetime.utcnow().isoformat() + 'Z'
        with suppress(Exception):
            events = self.calendar.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute().get('items', [])
            first_event = True
            for event in events:
                start = parser.parse(event['start'].get('dateTime', event['start'].get('date')))
                if start.timestamp() - time.time() < 900 and event['description'][0] != '*':
                    with suppress(Exception):
                        split_index = event['description'].find(';')
                        wug_members_str, stream_link = event['description'][:split_index], event['description'][split_index + 1:]
                        wug_members = wug_members_str.split(',')
                        if (link_start := stream_link.find('<a')) > 0:
                            stream_link = stream_link[:link_start]
                        elif stream_link.startswith('<a'):
                            stream_link = BeautifulSoup(stream_link, 'html.parser').find('a').contents[0]
                        colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), wug_members[0]) if len(wug_members) == 1 else Colour.teal()
                        embed_fields = []
                        embed_fields.append(('Time', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M} JST'.format(start.astimezone(pytz.timezone('Japan')))))
                        embed_fields.append(('WUG Members', ', '.join(wug_members)))
                        content = '**Starting in 15 Minutes**' if first_event else ''
                        await channel.send(content=content, embed=hkd.create_embed(title=event['summary'], colour=colour, url=stream_link, fields=embed_fields))
                        first_event = False
                        event['description'] = '*' + event['description']
                        self.calendar.events().update(calendarId='primary', eventId=event['id'], body=event).execute()

    @check_live_streams.before_loop
    async def before_check_live_streams(self):
        await self.bot.wait_until_ready()
