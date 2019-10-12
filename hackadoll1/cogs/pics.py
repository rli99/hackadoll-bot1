from contextlib import suppress

import hkdhelper as hkd
from discord import Colour
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

class Pics(commands.Cog):
    def __init__(self, bot, twitter_api):
        self.bot = bot
        self.twitter_api = twitter_api

    @commands.command(aliases=['tweet-pics', 'twitterpics', 'twitter-pics'])
    async def tweetpics(self, ctx, tweet_url: str):
        await ctx.channel.trigger_typing()
        for _ in range(3):
            with suppress(Exception):
                status_id = hkd.get_tweet_id_from_url(tweet_url)
                status = self.twitter_api.GetStatus(status_id=status_id, include_my_retweet=False)
                tweet = status.AsDict()
                media = tweet.get('media', [])
                if len(media) <= 1:
                    break
                pics = [p.get('media_url_https', '') for p in media[1:]]
                await hkd.send_content_with_delay(ctx, pics)
                return

    @commands.command(aliases=['insta-pics', 'instagrampics', 'instagram-pics'])
    @commands.cooldown(1, 10, BucketType.guild)
    async def instapics(self, ctx, post_url: str):
        for _ in range(3):
            with suppress(Exception):
                await ctx.channel.trigger_typing()
                json_data = hkd.get_json_from_instagram(post_url)
                images = json_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
                if len(images) <= 1:
                    return
                await hkd.send_content_with_delay(ctx, [i['node']['display_url'] for i in images[1:]])
                return

    @commands.command(aliases=['blog-pics'])
    @commands.cooldown(1, 10, BucketType.guild)
    async def blogpics(self, ctx, blog_url: str):
        await ctx.channel.trigger_typing()
        pics = hkd.get_pics_from_blog_post(blog_url.replace('//gamp.ameblo.jp/', '//ameblo.jp/'))
        if not pics:
            await ctx.send(embed=hkd.create_embed(description="Couldn't find any images.", colour=Colour.red()))
            return
        if len(pics) == 1:
            return
        await hkd.send_content_with_delay(ctx, pics[1:])

    @commands.command(name='aichan-blogpics')
    @commands.cooldown(1, 10, BucketType.guild)
    async def aichan_blogpics(self, ctx):
        await ctx.channel.trigger_typing()
        pics = hkd.get_pics_from_blog_post('https://ameblo.jp/eino-airi/')
        await hkd.send_content_with_delay(ctx, pics)
        if not pics:
            await ctx.send(embed=hkd.create_embed(description="Couldn't find any images.", colour=Colour.red()))
