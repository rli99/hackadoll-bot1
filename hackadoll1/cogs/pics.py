from contextlib import suppress
from urllib.request import urlretrieve

import hkdhelper as hkd
from discord import Colour, File
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

class Pics(commands.Cog):
    def __init__(self, bot, twitter_api):
        self.bot = bot
        self.twitter_api = twitter_api

    @commands.command(aliases=['tweet-pics', 'twitterpics', 'twitter-pics'])
    async def tweetpics(self, ctx, *tweet_url: str):
        await ctx.channel.trigger_typing()
        skip_first = int(not (len(tweet_url) > 1 and tweet_url[0] == 'all'))
        for _ in range(3):
            with suppress(Exception):
                status_id = hkd.get_tweet_id_from_url(tweet_url[int(not skip_first)])
                status = self.twitter_api.GetStatus(status_id=status_id, include_my_retweet=False)
                tweet = status.AsDict()
                if len(media := tweet.get('media', [])) <= 1 and skip_first:
                    break
                pics = [p.get('media_url_https', '') for p in media[skip_first:]]
                await hkd.send_content_with_delay(ctx, pics)
                return

    @commands.command(aliases=['insta-pics', 'instagrampics', 'instagram-pics'])
    @commands.cooldown(1, 10, BucketType.guild)
    async def instapics(self, ctx, *post_url: str):
        skip_first = int(not (len(post_url) > 1 and post_url[0] == 'all'))
        for _ in range(3):
            with suppress(Exception):
                await ctx.channel.trigger_typing()
                json_data = hkd.get_json_from_instagram(post_url[int(not skip_first)])
                if len(images := json_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']) <= 1 and skip_first:
                    return
                await hkd.send_content_with_delay(ctx, [i['node']['display_url'] for i in images[skip_first:]])
                return

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
            vid_filename = '{0}.mp4'.format(vid_id)
            urlretrieve('https://static.blog-video.jp/output/hq/{0}.mp4'.format(vid_id), vid_filename)
            await ctx.send(file=File('./{0}'.format(vid_filename)))

    @commands.command(name='aichan-blogpics')
    @commands.cooldown(1, 10, BucketType.guild)
    async def aichan_blogpics(self, ctx):
        await ctx.channel.trigger_typing()
        pics, vid_ids = hkd.get_media_from_blog_post('https://ameblo.jp/eino-airi/')
        if len(pics) <= 1 and not vid_ids:
            await ctx.send(embed=hkd.create_embed(description="Couldn't find any images.", colour=Colour.red()))
        if len(pics) > 1:
            await hkd.send_content_with_delay(ctx, pics[1:])
        for vid_id in vid_ids:
            vid_filename = '{0}.mp4'.format(vid_id)
            urlretrieve('https://static.blog-video.jp/output/hq/{0}.mp4'.format(vid_id), vid_filename)
            await ctx.send(file=File('./{0}'.format(vid_filename)))
