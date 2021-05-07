import asyncio
import os
import random
import subprocess
import time
from contextlib import suppress
from datetime import datetime
from html import unescape

import pytz
import requests
import hkdhelper as hkd
from bs4 import BeautifulSoup
from dateutil import parser
from discord import Colour, File, utils as disc_utils
from discord.ext import commands, tasks
from instaloader import Profile

class Loop(commands.Cog):
    def __init__(self, bot, config, muted_members, firebase_ref, calendar, twitter_api, insta_api):
        self.bot = bot
        self.config = config
        self.muted_members = muted_members
        self.firebase_ref = firebase_ref
        self.calendar = calendar
        self.twitter_api = twitter_api
        self.insta_api = insta_api
        self.check_mute_status.start()
        self.check_tweets.start()
        self.check_instagram.start()
        self.check_instagram_stories.start()
        self.check_live_streams.start()
        self.check_youtube_streams.start()
        self.check_showroom_lives.start()

    @tasks.loop(seconds=60.0)
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

    @check_mute_status.before_loop
    async def before_check_mute_status(self):
        await self.bot.wait_until_ready()

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

    @tasks.loop(minutes=20.0)
    async def check_instagram(self):
        channel = hkd.get_updates_channel(self.bot.guilds)
        with suppress(Exception):
            for instagram_id in self.firebase_ref.child('last_instagram_posts').get().keys():
                last_post_id = int(self.firebase_ref.child('last_instagram_posts/{0}'.format(instagram_id)).get())
                profile = Profile.from_username(self.insta_api.context, instagram_id)
                user_name = profile.full_name
                posted_updates = []
                for post in profile.get_posts():
                    if post.mediaid <= last_post_id:
                        break
                    post_text = post.caption
                    post_pic = post.url
                    post_link = 'https://www.instagram.com/p/{0}/'.format(post.shortcode)
                    posted_updates.append(post.mediaid)
                    if instagram_id in hkd.WUG_INSTAGRAM_IDS.values():
                        colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), hkd.dict_reverse(hkd.WUG_INSTAGRAM_IDS)[instagram_id])
                    else:
                        colour = Colour(0x242424)
                    author = {}
                    author['name'] = '{0} (@{1})'.format(user_name, instagram_id)
                    author['url'] = 'https://www.instagram.com/{0}/'.format(instagram_id)
                    author['icon_url'] = profile.profile_pic_url
                    await channel.send(embed=hkd.create_embed(author=author, title='Post by {0}'.format(user_name), description=post_text, colour=colour, url=post_link, image=post_pic))
                if posted_updates:
                    self.firebase_ref.child('last_instagram_posts/{0}'.format(instagram_id)).set(str(max(posted_updates)))
        self.check_instagram.change_interval(minutes=random.randint(20, 30))

    @check_instagram.before_loop
    async def before_check_instagram(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30.0)
    async def check_instagram_stories(self):
        channel = hkd.get_updates_channel(self.bot.guilds)
        with suppress(Exception):
            instaloader_args = ['instaloader', '--login={0}'.format(self.config['instagram_user']), '--sessionfile=./.instaloader-session', '--quiet', '--dirname-pattern={profile}', '--filename-pattern={profile}_{mediaid}', ':stories']
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
                    video_id = int(vid[:-4].split('_')[-1])
                    if video_id > last_story_id:
                        stories_to_upload.append(vid)
                        uploaded_story_ids.append(video_id)
                story_pics = [p for p in os.listdir(instagram_id) if p.endswith('.jpg')]
                for pic in story_pics:
                    pic_id = int(pic[:-4].split('_')[-1])
                    if pic_id > last_story_id and pic_id not in uploaded_story_ids:
                        stories_to_upload.append(pic)
                        uploaded_story_ids.append(pic_id)
                if uploaded_story_ids:
                    profile = Profile.from_username(self.insta_api.context, instagram_id)
                    user_name = profile.full_name
                    if instagram_id in hkd.WUG_INSTAGRAM_IDS.values():
                        colour = hkd.get_oshi_colour(hkd.get_wug_guild(self.bot.guilds), hkd.dict_reverse(hkd.WUG_INSTAGRAM_IDS)[instagram_id])
                    else:
                        colour = Colour(0x242424)
                    author = {}
                    author['name'] = '{0} (@{1})'.format(user_name, instagram_id)
                    author['url'] = 'https://www.instagram.com/{0}/'.format(instagram_id)
                    author['icon_url'] = profile.profile_pic_url
                    story_link = 'https://www.instagram.com/stories/{0}/'.format(instagram_id)
                first_upload = True
                for story in sorted(stories_to_upload):
                    if first_upload:
                        await channel.send(embed=hkd.create_embed(author=author, title='Instagram Story Updated by {0}'.format(user_name), colour=colour, url=story_link))
                        first_upload = False
                    await channel.send(file=File('./{0}/{1}'.format(instagram_id, story)))
                if uploaded_story_ids:
                    self.firebase_ref.child('last_instagram_stories/{0}'.format(instagram_id)).set(str(max(uploaded_story_ids)))
        self.check_instagram.change_interval(minutes=random.randint(30, 50))

    @check_instagram_stories.before_loop
    async def before_check_instagram_stories(self):
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

    @tasks.loop(seconds=30.0)
    async def check_youtube_streams(self):
        channel = hkd.get_seiyuu_channel(self.bot.guilds)
        with suppress(Exception):
            stream_status = self.firebase_ref.child('youtube_stream_status').get().keys()
            for member in stream_status:
                channel_id = hkd.WUG_YOUTUBE_CHANNELS[member]
                status = self.firebase_ref.child('youtube_stream_status/{0}/status'.format(member)).get()
                last_online = float(self.firebase_ref.child('youtube_stream_status/{0}/last_online'.format(member)).get())
                last_video_id = self.firebase_ref.child('youtube_stream_status/{0}/video_id'.format(member)).get()
                videos = hkd.get_video_data_from_youtube(channel_id)
                is_live = False
                if len(videos) < 10:
                    for video in videos:
                        renderer = video['gridVideoRenderer']
                        if (badges := renderer.get('badges')) and [b for b in badges if b['metadataBadgeRenderer']['label'] == 'LIVE NOW']:
                            is_live = True
                            video_id = renderer['videoId']
                            self.firebase_ref.child('youtube_stream_status/{0}/last_online'.format(member)).set(time.time())
                            self.firebase_ref.child('youtube_stream_status/{0}/video_id'.format(member)).set(video_id)
                            if status != 'LIVE':
                                if time.time() - last_online > 300 or last_video_id != video_id:
                                    channel_name = member.title()
                                    if short_desc := renderer.get('shortBylineText'):
                                        if runs := short_desc['runs']:
                                            channel_name = runs[0].get('text', hkd.parse_oshi_name(member).title())
                                    await channel.send('{0} LIVE NOW at https://www.youtube.com/watch?v={1}'.format(channel_name, video_id))
                                self.firebase_ref.child('youtube_stream_status/{0}/status'.format(member)).set('LIVE')
                            break
                        elif 'thumbnailOverlays' in renderer:
                            overlay = renderer['thumbnailOverlays'][0]
                            if overlay['thumbnailOverlayTimeStatusRenderer']['text']['runs'][0].get('text') == 'LIVE':
                                is_live = True
                                video_id = renderer['videoId']
                                self.firebase_ref.child('youtube_stream_status/{0}/last_online'.format(member)).set(time.time())
                                self.firebase_ref.child('youtube_stream_status/{0}/video_id'.format(member)).set(video_id)
                                if status != 'LIVE':
                                    if time.time() - last_online > 300 or last_video_id != video_id:
                                        channel_name = hkd.parse_oshi_name(member).title()
                                        with suppress(Exception):
                                            label = renderer['title']['accessibility']['accessibilityData']['label']
                                            channel_name = label.split(' ')[-3]
                                        await channel.send('{0} LIVE NOW at https://www.youtube.com/watch?v={1}'.format(channel_name, video_id))
                                    self.firebase_ref.child('youtube_stream_status/{0}/status'.format(member)).set('LIVE')
                                break
                if status == 'LIVE' and not is_live:
                    self.firebase_ref.child('youtube_stream_status/{0}/status'.format(member)).set('OFFLINE')

    @check_youtube_streams.before_loop
    async def before_check_youtube_streams(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=30.0)
    async def check_showroom_lives(self):
        channel = hkd.get_seiyuu_channel(self.bot.guilds)
        for member, room_id in hkd.WUG_SHOWROOM_IDS.items():
            status = self.firebase_ref.child('showroom_live_status/{0}/status'.format(member)).get()
            last_online = float(self.firebase_ref.child('showroom_live_status/{0}/last_online'.format(member)).get())
            with suppress(Exception):
                sr_data = requests.get('https://showroom-live.com/api/room/profile?room_id={0}'.format(room_id), headers=hkd.get_random_header()).json()
                if sr_data['is_onlive']:
                    self.firebase_ref.child('showroom_live_status/{0}/last_online'.format(member)).set(time.time())
                    if status != 'LIVE'and time.time() - last_online > 300:
                        await channel.send(sr_data.get('share_text_live', '{0} Broadcasting!\n{1}'.format(sr_data['room_name'], sr_data['share_url_live'])))
                    self.firebase_ref.child('showroom_live_status/{0}/status'.format(member)).set('LIVE')
                else:
                    self.firebase_ref.child('showroom_live_status/{0}/status'.format(member)).set('OFFLINE')

    @check_showroom_lives.before_loop
    async def before_check_showroom_lives(self):
        await self.bot.wait_until_ready()
