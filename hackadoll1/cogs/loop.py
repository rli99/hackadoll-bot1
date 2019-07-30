import asyncio
import json
import os
import subprocess
import time
from contextlib import suppress
from datetime import datetime
from html import unescape

import requests
import pytz
import hkdhelper as hkd
from bs4 import BeautifulSoup
from dateutil import parser
from discord import Colour, File, utils as disc_utils
from discord.ext import commands, tasks

class Loop(commands.Cog):
    def __init__(self, bot, config, muted_members, firebase_ref, twitter_api, calendar):
        self.bot = bot
        self.config = config
        self.muted_members = muted_members
        self.firebase_ref = firebase_ref
        self.twitter_api = twitter_api
        self.calendar = calendar
        self.check_mute_status.start()
        self.check_tweets.start()
        self.check_instagram.start()
        self.check_instagram_stories.start()
        self.check_live_streams.start()

    @tasks.loop(seconds=30.0)
    async def check_mute_status(self):
        members_to_unmute = []
        for member_id in self.muted_members:
            if time.time() > float(self.muted_members[member_id]):
                self.firebase_ref.child('muted_members/{0}'.format(member_id)).delete()
                members_to_unmute.append(member_id)
                guild = hkd.get_wug_guild(self.bot.guilds)
                member = disc_utils.get(guild.members, id=int(member_id))
                await member.remove_roles(hkd.get_muted_role(guild))
        for member_id in members_to_unmute:
            self.muted_members.pop(member_id)
        return

    @check_mute_status.before_loop
    async def before_check_mute_status(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=20.0)
    async def check_tweets(self):
        channel = hkd.get_updates_channel(self.bot.guilds)
        for _ in range(3):
            with suppress(Exception):
                twitter_user_ids = self.firebase_ref.child('last_userid_tweets').get().keys()
                for user_id_str in twitter_user_ids:
                    user_id = int(user_id_str)
                    last_tweet_id = int(self.firebase_ref.child('last_userid_tweets/{0}'.format(user_id)).get())
                    posted_tweets = []
                    statuses = self.twitter_api.GetUserTimeline(user_id=user_id, since_id=last_tweet_id, count=40, include_rts=False)
                    for status in reversed(statuses):
                        tweet = status.AsDict()
                        user = tweet['user']
                        name = user['screen_name']
                        if str(tweet.get('in_reply_to_user_id', user_id)) not in twitter_user_ids:
                            continue
                        await channel.trigger_typing()
                        await asyncio.sleep(1)
                        tweet_id = tweet['id']
                        posted_tweets.append(tweet_id)
                        tweet_content = unescape(tweet['full_text'])
                        if user_id in hkd.WUG_TWITTER_IDS.values():
                            colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), hkd.dict_reverse(hkd.WUG_TWITTER_IDS)[user_id])
                        else:
                            colour = Colour.light_grey()
                        author = {}
                        author['name'] = '{0} (@{1})'.format(user['name'], user['screen_name'])
                        author['url'] = 'https://twitter.com/{0}'.format(name)
                        author['icon_url'] = user['profile_image_url_https']
                        image = ''
                        expanded_urls = tweet['urls']
                        if expanded_urls:
                            expanded_url = expanded_urls[0].get('expanded_url', '')
                            if expanded_url and hkd.is_blog_post(expanded_url):
                                soup = hkd.get_html_from_url(expanded_url)
                                blog_entry = soup.find(attrs={'class': 'skin-entryBody'})
                                blog_images = [p['src'] for p in blog_entry.find_all('img') if '?caw=' in p['src'][-9:]]
                                if blog_images:
                                    image = blog_images[0]
                        media = tweet.get('media', '')
                        if media:
                            image = media[0].get('media_url_https', '')
                        await channel.send(embed=hkd.create_embed(author=author, title='Tweet by {0}'.format(user['name']), description=tweet_content, colour=colour, url='https://twitter.com/{0}/status/{1}'.format(name, tweet_id), image=image))
                    if posted_tweets:
                        self.firebase_ref.child('last_userid_tweets/{0}'.format(user_id)).set(str(max(posted_tweets)))
                return

    @check_tweets.before_loop
    async def before_check_tweets(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30.0)
    async def check_instagram(self):
        channel = hkd.get_updates_channel(self.bot.guilds)
        for _ in range(3):
            with suppress(Exception):
                for instagram_id in self.firebase_ref.child('last_instagram_posts').get().keys():
                    last_post_id = int(self.firebase_ref.child('last_instagram_posts/{0}'.format(instagram_id)).get())
                    response = requests.get('https://www.instagram.com/{0}/'.format(instagram_id), headers=hkd.get_random_header())
                    soup = BeautifulSoup(response.text, 'html.parser')
                    script = soup.find('body').find('script')
                    json_data = json.loads(script.text.strip().replace('window._sharedData =', '').replace(';', ''))
                    user_data = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
                    user_name = user_data['full_name']
                    user_id = user_data['username']
                    profile_pic = user_data['profile_pic_url_hd']
                    timeline = user_data['edge_owner_to_timeline_media']['edges']
                    posted_updates = []
                    for post in timeline:
                        post_content = post['node']
                        post_id = int(post_content['id'])
                        if post_id <= last_post_id:
                            break
                        post_text = post_content['edge_media_to_caption']['edges'][0]['node']['text']
                        post_pic = post_content['display_url']
                        post_link = 'https://www.instagram.com/p/{0}/'.format(post_content['shortcode'])
                        posted_updates.append(post_id)
                        if instagram_id in hkd.WUG_INSTAGRAM_IDS.values():
                            colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), hkd.dict_reverse(hkd.WUG_INSTAGRAM_IDS)[instagram_id])
                        else:
                            colour = Colour.light_grey()
                        author = {}
                        author['name'] = '{0} (@{1})'.format(user_name, user_id)
                        author['url'] = 'https://www.instagram.com/{0}/'.format(instagram_id)
                        author['icon_url'] = profile_pic
                        await channel.send(embed=hkd.create_embed(author=author, title='Post by {0}'.format(user_name), description=post_text, colour=colour, url=post_link, image=post_pic))
                    if posted_updates:
                        self.firebase_ref.child('last_instagram_posts/{0}'.format(instagram_id)).set(str(max(posted_updates)))
                return

    @check_instagram.before_loop
    async def before_check_instagram(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=90.0)
    async def check_instagram_stories(self):
        channel = hkd.get_updates_channel(self.bot.guilds)
        with suppress(Exception):
            instaloader_args = ['instaloader', '--login={0}'.format(self.config['instagram_user']), '--sessionfile={0}'.format('./.instaloader-session'), '--quiet', '--dirname-pattern={profile}', '--filename-pattern={profile}_{mediaid}', ':stories']
            proc = subprocess.Popen(args=instaloader_args)
            while proc.poll() is None:
                await asyncio.sleep(1)
            for instagram_id in self.firebase_ref.child('last_instagram_stories').get().keys():
                if not os.path.isdir(instagram_id):
                    continue
                story_videos = [v for v in os.listdir(instagram_id) if v.endswith('.mp4')]
                last_story_id = int(self.firebase_ref.child('last_instagram_stories/{0}'.format(instagram_id)).get())
                uploaded_story_ids = []
                stories_to_upload = []
                for vid in story_videos:
                    video_id = int(vid[:-4].rsplit('_')[1])
                    if video_id > last_story_id:
                        stories_to_upload.append(vid)
                        uploaded_story_ids.append(video_id)
                story_pics = [p for p in os.listdir(instagram_id) if p.endswith('.jpg')]
                for pic in story_pics:
                    pic_id = int(pic[:-4].rsplit('_')[1])
                    if pic_id > last_story_id and pic_id not in uploaded_story_ids:
                        stories_to_upload.append(pic)
                        uploaded_story_ids.append(pic_id)
                if uploaded_story_ids:
                    response = requests.get('https://www.instagram.com/{0}/'.format(instagram_id), headers=hkd.get_random_header())
                    soup = BeautifulSoup(response.text, 'html.parser')
                    script = soup.find('body').find('script')
                    json_data = json.loads(script.text.strip().replace('window._sharedData =', '').replace(';', ''))
                    user_data = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
                    user_name = user_data['full_name']
                    user_id = user_data['username']
                    profile_pic = user_data['profile_pic_url_hd']
                    if instagram_id in hkd.WUG_INSTAGRAM_IDS.values():
                        colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), hkd.dict_reverse(hkd.WUG_INSTAGRAM_IDS)[instagram_id])
                    else:
                        colour = Colour.light_grey()
                    author = {}
                    author['name'] = '{0} (@{1})'.format(user_name, user_id)
                    author['url'] = 'https://www.instagram.com/{0}/'.format(instagram_id)
                    author['icon_url'] = profile_pic
                    story_link = 'https://www.instagram.com/stories/{0}/'.format(instagram_id)
                first_upload = True
                for story in sorted(stories_to_upload):
                    if first_upload:
                        await channel.send(embed=hkd.create_embed(author=author, title='Instagram Story Updated by {0}'.format(user_name), colour=colour, url=story_link))
                        first_upload = False
                    await channel.send(file=File('./{0}/{1}'.format(instagram_id, story)))
                if uploaded_story_ids:
                    self.firebase_ref.child('last_instagram_stories/{0}'.format(instagram_id)).set(str(max(uploaded_story_ids)))
        return

    @check_instagram_stories.before_loop
    async def before_check_instagram_stories(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30.0)
    async def check_live_streams(self):
        channel = hkd.get_seiyuu_channel(self.bot.guilds)
        now = datetime.utcnow().isoformat() + 'Z'
        for _ in range(3):
            with suppress(Exception):
                events = self.calendar.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute().get('items', [])
                first_event = True
                for event in events:
                    start = parser.parse(event['start'].get('dateTime', event['start'].get('date')))
                    if start.timestamp() - time.time() < 900 and event['description'][0] != '*':
                        split_index = event['description'].find(';')
                        wug_members_str, stream_link = event['description'][:split_index], event['description'][split_index + 1:]
                        wug_members = wug_members_str.split(',')
                        if stream_link[0] == '<':
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
                return

    @check_live_streams.before_loop
    async def before_check_live_streams(self):
        await self.bot.wait_until_ready()
