import re
from contextlib import suppress
from urllib.request import urlretrieve

import hkdhelper as hkd
from discord import Colour, File
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from instaloader import Post, Profile

class Pics(commands.Cog):
    def __init__(self, bot, twitter_api, insta_api):
        self.bot = bot
        self.twitter_api = twitter_api
        self.insta_api = insta_api

    @commands.command(aliases=['tweet-pics', 'twitterpics', 'twitter-pics'])
    async def tweetpics(self, ctx, *tweet_url: str):
        await ctx.channel.trigger_typing()
        if tweet_url[0] == 'all':
            if len(tweet_url) == 1:
                return
            skip_first = False
        else:
            skip_first = True
        status_id = hkd.get_tweet_id_from_url(tweet_url[not skip_first])
        status = self.twitter_api.GetStatus(status_id=status_id, include_my_retweet=False)
        tweet = status.AsDict()
        if len(media := tweet.get('media', [])) <= 1 and skip_first:
            return
        pics = [p.get('media_url_https', '') for p in media[skip_first:]]
        await hkd.send_content_with_delay(ctx, pics)

    @commands.command(aliases=['insta-pics', 'instagrampics', 'instagram-pics'])
    @commands.cooldown(1, 10, BucketType.guild)
    async def instapics(self, ctx, *post_url: str):
        await ctx.channel.trigger_typing()
        if post_url[0] == 'all':
            if len(post_url) == 1:
                return
            skip_first = False
        else:
            skip_first = True
        if not (shortcode := hkd.get_id_from_url(post_url[not skip_first], '/p/', '/')):
            return
        images, videos = [], []
        post = Post.from_shortcode(self.insta_api.context, shortcode)
        if post.typename == 'GraphSidecar':
            for i, node in enumerate(post.get_sidecar_nodes()):
                if not node.is_video:
                    if not (i == 0 and skip_first):
                        images.append(node.display_url)
                else:
                    videos.append(node.video_url)
        elif post.typename == 'GraphImage':
            images.append(post.url)
        elif post.typename == 'GraphVideo':
            videos.append(post.video_url)
        await hkd.send_content_with_delay(ctx, images)
        await hkd.send_content_with_delay(ctx, videos)

    @commands.command(aliases=['blog-pics'])
    @commands.cooldown(1, 10, BucketType.guild)
    async def blogpics(self, ctx, blog_url: str):
        await ctx.channel.trigger_typing()
        pics, vid_ids = hkd.get_media_from_blog_post(blog_url.replace('//gamp.ameblo.jp/', '//ameblo.jp/'))
        if len(pics) <= 1 and not vid_ids:
            await ctx.send(embed=hkd.create_embed(description="Couldn't find any images.", colour=Colour.red()))
        if len(pics) > 1:
            await hkd.send_content_with_delay(ctx, pics[1:])
        for vid_id in vid_ids:
            video_file = './{0}.mp4'.format(vid_id)
            video_link = 'https://static.blog-video.jp/output/hq/{0}.mp4'.format(vid_id)
            urlretrieve(video_link, video_file)
            await hkd.send_video_check_filesize(ctx, video_file, video_link)

    @commands.command(name='aichan-blogpics')
    @commands.cooldown(1, 10, BucketType.guild)
    async def aichan_blogpics(self, ctx):
        await ctx.channel.trigger_typing()
        pics, vid_ids = hkd.get_media_from_blog_post('https://ameblo.jp/eino-airi/')
        if not pics and not vid_ids:
            await ctx.send(embed=hkd.create_embed(description="Couldn't find any images.", colour=Colour.red()))
            return
        await hkd.send_content_with_delay(ctx, pics)
        for vid_id in vid_ids:
            video_file = './{0}.mp4'.format(vid_id)
            video_link = 'https://static.blog-video.jp/output/hq/{0}.mp4'.format(vid_id)
            urlretrieve(video_link, video_file)
            await hkd.send_video_check_filesize(ctx, video_file, video_link)

    @commands.command(aliases=['profile-pic'])
    @commands.cooldown(1, 10, BucketType.guild)
    async def profilepic(self, ctx, account_url: str):
        await ctx.channel.trigger_typing()
        if 'instagram.com' in account_url:
            account_id = hkd.get_id_from_url(account_url, 'instagram.com/', '/')
            profile = Profile.from_username(self.insta_api.context, account_id)
            await ctx.send(profile.profile_pic_url)
        elif 'twitter.com' in account_url:
            account_name = hkd.get_id_from_url(account_url, 'twitter.com/', '/')
            user = self.twitter_api.GetUser(screen_name=account_name)
            await ctx.send(''.join(user.AsDict().get('profile_image_url_https').rsplit('_normal', 1)))
        elif 'youtube.com' in account_url:
            html_response = hkd.get_html_from_url(account_url)
            await ctx.send(re.sub(r'=s[\d]+.*', '', html_response.find(property='og:image').get('content')))
