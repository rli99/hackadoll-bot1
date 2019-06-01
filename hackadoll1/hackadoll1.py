import asyncio, discord, json, os, pycountry, pytz, requests, subprocess, time, twitter
import hkdhelper as hkd
from apiclient.discovery import build
from bs4 import BeautifulSoup
from calendar import month_name
from contextlib import suppress
from datetime import datetime
from dateutil import parser
from decimal import Decimal
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from firebase_admin import credentials, db, initialize_app
from forex_python.converter import CurrencyRates
from googletrans import Translator
from hkdhelper import create_embed, dict_reverse, get_html_from_url, get_muted_role, get_oshi_colour, get_seiyuu_channel, get_updates_channel, get_wug_guild, get_wug_role, parse_oshi_name
from html import unescape
from httplib2 import Http
from humanfriendly import format_timespan
from oauth2client import file
from operator import itemgetter
from random import randrange
from timezonefinder import TimezoneFinder
from urllib.parse import quote

config = hkd.parse_config()
bot = commands.Bot(command_prefix=('!', 'ichigo ', 'alexa ', 'Ichigo ', 'Alexa '))
bot.remove_command('help')
certificate = credentials.Certificate(config['firebase_credentials'])
firebase = initialize_app(certificate, { 'databaseURL': config['firebase_db'] })
firebase_ref = db.reference()
muted_members = firebase_ref.child('muted_members').get() or {}
twitter_api = twitter.Api(consumer_key=config['consumer_key'], consumer_secret=config['consumer_secret'], access_token_key=config['access_token_key'], access_token_secret=config['access_token_secret'], tweet_mode='extended')
calendar = build('calendar', 'v3', http=file.Storage('credentials.json').get().authorize(Http()))

@bot.event
async def on_ready():
    print('\n-------------\nLogged in as: {0} ({1})\n-------------\n'.format(bot.user.name, bot.user.id))

@bot.event
async def check_mute_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        members_to_unmute = []
        for member_id in muted_members:
            if time.time() > float(muted_members[member_id]):
                firebase_ref.child('muted_members/{0}'.format(member_id)).delete()
                members_to_unmute.append(member_id)
                guild = get_wug_guild(bot.guilds)
                member = discord.utils.get(guild.members, id=int(member_id))
                await member.remove_roles(get_muted_role(guild))
        for member_id in members_to_unmute:
            muted_members.pop(member_id)
        await asyncio.sleep(30)

@bot.event
async def check_tweets():
    await bot.wait_until_ready()
    while not bot.is_closed():
        channel = get_updates_channel(bot.guilds)
        for _ in range(3):
            with suppress(Exception):
                twitter_user_ids = firebase_ref.child('last_userid_tweets').get().keys()
                for user_id_str in twitter_user_ids:
                    user_id = int(user_id_str)
                    last_tweet_id = int(firebase_ref.child('last_userid_tweets/{0}'.format(user_id)).get())
                    posted_tweets = []
                    statuses = twitter_api.GetUserTimeline(user_id=user_id, since_id=last_tweet_id, count=40, include_rts=False)
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
                            colour = get_oshi_colour(get_wug_guild(bot.guilds), dict_reverse(hkd.WUG_TWITTER_IDS)[user_id])
                        else:
                            colour = discord.Colour.light_grey()
                        author = {}
                        author['name'] = '{0} (@{1})'.format(user['name'], user['screen_name'])
                        author['url'] = 'https://twitter.com/{0}'.format(name)
                        author['icon_url'] = user['profile_image_url_https']
                        image = ''
                        if hkd.is_blog_post(tweet_content):
                            soup = get_html_from_url(tweet_content.split('⇒')[1].split()[0])
                            blog_entry = soup.find(attrs={ 'class': 'skin-entryBody' })
                            blog_images = [p['src'] for p in blog_entry.find_all('img') if '?caw=' in p['src'][-9:]]
                            if blog_images:
                                image = blog_images[0]
                        media = tweet.get('media', '')
                        if media:
                            image = media[0].get('media_url_https', '')
                        await channel.send(embed=create_embed(author=author, title='Tweet by {0}'.format(user['name']), description=tweet_content, colour=colour, url='https://twitter.com/{0}/status/{1}'.format(name, tweet_id), image=image))
                    if posted_tweets:
                        firebase_ref.child('last_userid_tweets/{0}'.format(user_id)).set(str(max(posted_tweets)))
                break
        await asyncio.sleep(20)

@bot.event
async def check_instagram():
    await bot.wait_until_ready()
    while not bot.is_closed():
        channel = get_updates_channel(bot.guilds)
        for _ in range(3):
            with suppress(Exception):
                for instagram_id in firebase_ref.child('last_instagram_posts').get().keys():
                    last_post_id = int(firebase_ref.child('last_instagram_posts/{0}'.format(instagram_id)).get())
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
                            colour = get_oshi_colour(get_wug_guild(bot.guilds), dict_reverse(hkd.WUG_INSTAGRAM_IDS)[instagram_id])
                        else:
                            colour = discord.Colour.light_grey()
                        author = {}
                        author['name'] = '{0} (@{1})'.format(user_name, user_id)
                        author['url'] = 'https://www.instagram.com/{0}/'.format(instagram_id)
                        author['icon_url'] = profile_pic
                        await channel.send(embed=create_embed(author=author, title='Post by {0}'.format(user_name), description=post_text, colour=colour, url=post_link, image=post_pic))
                    if posted_updates:
                        firebase_ref.child('last_instagram_posts/{0}'.format(instagram_id)).set(str(max(posted_updates)))
                break
        await asyncio.sleep(30)

@bot.event
async def check_instagram_stories():
    await bot.wait_until_ready()
    while not bot.is_closed():
        channel = get_updates_channel(bot.guilds)
        with suppress(Exception):
            instaloader_args = ['instaloader', '--login={0}'.format(config['instagram_user']), '--sessionfile={0}'.format('./.instaloader-session'), '--quiet', '--dirname-pattern={profile}', '--filename-pattern={profile}_{mediaid}', ':stories']
            proc = subprocess.Popen(args=instaloader_args)
            while proc.poll() is None:
                await asyncio.sleep(1)
            for instagram_id in firebase_ref.child('last_instagram_stories').get().keys():
                if not os.path.isdir(instagram_id):
                    continue
                story_videos = [v for v in os.listdir(instagram_id) if v.endswith('.mp4')]
                last_story_id = int(firebase_ref.child('last_instagram_stories/{0}'.format(instagram_id)).get())
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
                        colour = get_oshi_colour(get_wug_guild(bot.guilds), dict_reverse(hkd.WUG_INSTAGRAM_IDS)[instagram_id])
                    else:
                        colour = discord.Colour.light_grey()
                    author = {}
                    author['name'] = '{0} (@{1})'.format(user_name, user_id)
                    author['url'] = 'https://www.instagram.com/{0}/'.format(instagram_id)
                    author['icon_url'] = profile_pic
                    story_link = 'https://www.instagram.com/stories/{0}/'.format(instagram_id)
                first_upload = True
                for story in sorted(stories_to_upload):
                    if first_upload:
                        await channel.send(embed=create_embed(author=author, title='Instagram Story Updated by {0}'.format(user_name), colour=colour, url=story_link))
                        first_upload = False
                    await channel.send(file=discord.File('./{0}/{1}'.format(instagram_id, story)))
                if uploaded_story_ids:
                    firebase_ref.child('last_instagram_stories/{0}'.format(instagram_id)).set(str(max(uploaded_story_ids)))
        await asyncio.sleep(90)

@bot.event
async def check_live_streams():
    await bot.wait_until_ready()
    while not bot.is_closed():
        channel = get_seiyuu_channel(bot.guilds)
        now = datetime.utcnow().isoformat() + 'Z'
        for _ in range(3):
            with suppress(Exception):
                events = calendar.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute().get('items', [])
                first_event = True
                for event in events:
                    start = parser.parse(event['start'].get('dateTime', event['start'].get('date')))
                    if start.timestamp() - time.time() < 900 and event['description'][0] != '*':
                        split_index = event['description'].find(';')
                        wug_members_str, stream_link = event['description'][:split_index], event['description'][split_index + 1:]
                        wug_members = wug_members_str.split(',')
                        if stream_link[0] == '<':
                            stream_link = BeautifulSoup(stream_link, 'html.parser').find('a').contents[0]
                        colour = get_oshi_colour(get_wug_guild(bot.guilds), wug_members[0]) if len(wug_members) == 1 else discord.Colour.teal()
                        embed_fields = []
                        embed_fields.append(('Time', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M} JST'.format(start.astimezone(pytz.timezone('Japan')))))
                        embed_fields.append(('WUG Members', ', '.join(wug_members)))
                        content = '**Starting in 15 Minutes**' if first_event else ''
                        await channel.send(content=content, embed=create_embed(title=event['summary'], colour=colour, url=stream_link, fields=embed_fields))
                        first_event = False
                        event['description'] = '*' + event['description']
                        calendar.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
                break
        await asyncio.sleep(30)

@bot.group()
async def help(ctx):
    await ctx.channel.trigger_typing()
    if ctx.invoked_subcommand is None:
        embed_fields = []
        embed_fields.append(('!help', 'Show this help message.'))
        embed_fields.append(('!help mod-commands', 'Show help for moderator-only commands.'))
        embed_fields.append(('!help roles', 'Show help for role commands.'))
        embed_fields.append(('!help events', 'Show help for event commands.'))
        embed_fields.append(('!help tags', 'Show help for tag commands.'))
        embed_fields.append(('!mv *song*', 'Show full MV of a song.'))
        embed_fields.append(('!mv-list', 'Show list of available MVs.'))
        embed_fields.append(('!userinfo', 'Show your user information.'))
        embed_fields.append(('!serverinfo', 'Show server information.'))
        embed_fields.append(('!aichan-blogpics', 'Get pictures from the latest blog post by Aichan.'))
        embed_fields.append(('!seiyuu-vids', 'Show link to the wiki page with WUG seiyuu content.'))
        embed_fields.append(('!tl *japanese text*', 'Translate the provided Japanese text into English via Google Translate.'))
        embed_fields.append(('!currency *amount* *x* to *y*', 'Convert *amount* of *x* currency to *y* currency, e.g. **!currency** 12.34 AUD to USD'))
        embed_fields.append(('!weather *city*, *country*', 'Show weather information for *city*, *country* (optional), e.g. **!weather** Melbourne, Australia'))
        embed_fields.append(('!choose *options*', 'Randomly choose from one of the provided options, e.g. **!choose** option1 option2'))
        embed_fields.append(('!yt *query*', 'Gets the top result from YouTube based on the provided search terms.'))
        embed_fields.append(('!dl-vid *url*', 'Attempts to download the video from the specified URL using youtube-dl.'))
        embed_fields.append(('!onmusu *member*', 'Show the Onsen Musume profile for the character of the specified member.'))
        await ctx.send(content='**Available Commands**', embed=create_embed(fields=embed_fields))

@help.command(name='mod-commands', aliases=['mod', 'mods'])
async def mod_commands(ctx):
    embed_fields = []
    embed_fields.append(('!kick *member*', 'Kick a member.'))
    embed_fields.append(('!ban *member*', 'Ban a member.'))
    embed_fields.append(('!mute *member* *duration*', 'Mute a member for *duration* minutes.'))
    embed_fields.append(('!unmute *member*', 'Unmute a member.'))
    await ctx.send(content='**Commands for Moderators**', embed=create_embed(fields=embed_fields))

@help.command(aliases=['role'])
@commands.guild_only()
async def roles(ctx):
    description = 'Users can have any of the 7 WUG member roles. Use **!oshihen** *member* to get the role you want.\n\n'
    for oshi in hkd.WUG_ROLE_IDS.keys():
        description += '**!oshihen** {0} for {1.mention}\n'.format(oshi.title(), get_wug_role(ctx.guild, oshi))
    description += "\nNote that using **!oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **!oshimashi** *member* instead. To get all 7 roles, use **!hakooshi**. Use **!kamioshi** *member* to specify which member you want to set as your highest role (you will get that member's colour).\n\n"
    description += 'Use **!oshi-count** to show the number of members with each WUG member role, or **!kamioshi-count** to show the number of members with each WUG member role as their highest role.\n'
    await ctx.send(content='**Commands for Roles**', embed=create_embed(description=description))

@help.command(aliases=['event'])
async def events(ctx):
    embed_fields = []
    embed_fields.append(('!events *date*', 'Get information for events involving WUG members on the specified date, e.g. **!events** apr 1. If *date* not specified, finds events happening today.'))
    embed_fields.append(('!eventsin *month* *member*', 'Get information for events involving WUG members for the specified month and member, e.g. **!eventsin** April Mayushii. If *member* not specified, searches for Wake, Up Girls! related events instead. Searches events from this month onwards only.'))
    await ctx.send(content='**Commands for Searching Events**', embed=create_embed(fields=embed_fields))

@help.command(aliases=['tag'])
async def tags(ctx):
    embed_fields = []
    embed_fields.append(('!tagcreate *tag_name* *content*', 'Create a tag. Use one word (no spaces) for tag names.'))
    embed_fields.append(('!tagupdate *tag_name* *updated_content*', 'Update an existing tag.'))
    embed_fields.append(('!tagdelete *tag_name*', 'Delete an existing tag.'))
    embed_fields.append(('!tagsearch', 'Shows a list of all existing tags.'))
    embed_fields.append(('!tag *tag_name*', 'Display a saved tag.'))
    await ctx.send(content='**Commands for Using Tags**', embed=create_embed(fields=embed_fields))

@bot.command()
@commands.guild_only()
async def kick(ctx, member: discord.Member):
    await ctx.channel.trigger_typing()
    if ctx.author.guild_permissions.kick_members:
        if member.guild_permissions.administrator:
            await ctx.send(embed=create_embed(title='Moderators cannot be kicked.', colour=discord.Colour.red()))
            return
        await member.kick()
        await ctx.send(embed=create_embed(title='{0} has been kicked.'.format(member)))
        firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        return
    await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def ban(ctx, member: discord.Member):
    await ctx.channel.trigger_typing()
    if ctx.author.guild_permissions.ban_members:
        await member.ban()
        await ctx.send(embed=create_embed(title='{0} has been banned.'.format(member)))
        firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        return
    await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def mute(ctx, member: discord.Member, duration: int):
    await ctx.channel.trigger_typing()
    if ctx.author.guild_permissions.kick_members:
        if member.guild_permissions.administrator:
            await ctx.send(embed=create_embed(title='Moderators cannot be muted.', colour=discord.Colour.red()))
            return
        if duration > 0:
            mute_endtime = time.time() + duration * 60
            firebase_ref.child('muted_members/{0}'.format(member.id)).set(str(mute_endtime))
            muted_members[str(member.id)] = mute_endtime
            await member.add_roles(get_muted_role(ctx.guild))
            await ctx.send(embed=create_embed(description='{0.mention} has been muted for {1}.'.format(member, format_timespan(duration * 60))))
        else:
            await ctx.send(embed=create_embed(title='Please specify a duration greater than 0.', colour=discord.Colour.red()))
    else:
        await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def unmute(ctx, member: discord.Member):
    await ctx.channel.trigger_typing()
    if ctx.author.guild_permissions.kick_members:
        firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        muted_members.pop(member.id)
        await member.remove_roles(get_muted_role(ctx.guild))
        await ctx.send(embed=create_embed(description='{0.mention} has been unmuted.'.format(member)))
    else:
        await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def oshihen(ctx, member: str=''):
    await ctx.channel.trigger_typing()
    role = get_wug_role(ctx.guild, member)
    if role is None:
        await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=discord.Colour.red()))
        return
    roles_to_remove = []
    for existing_role in ctx.author.roles:
        if existing_role.id in hkd.WUG_ROLE_IDS.values() or existing_role.id in hkd.WUG_KAMIOSHI_ROLE_IDS.values():
            roles_to_remove.append(existing_role)
    if len(roles_to_remove) == 1 and roles_to_remove[0].name == role.name:
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=discord.Colour.red()))
    elif len(roles_to_remove) > 0:
        await ctx.author.remove_roles(*roles_to_remove)
        await asyncio.sleep(1)
    await ctx.author.add_roles(role)
    await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you have oshihened to the **{1}** role {2.mention}.'.format(ctx, member.title(), role), colour=role.colour))

@bot.command()
@commands.guild_only()
async def oshimashi(ctx, member: str=''):
    await ctx.channel.trigger_typing()
    role = get_wug_role(ctx.guild, member)
    if role is None:
        await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=discord.Colour.red()))
        return
    if role not in ctx.author.roles:
        await ctx.author.add_roles(role)
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you now have the **{1}** oshi role {2.mention}.'.format(ctx, member.title(), role), colour=role.colour))
    else:
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def hakooshi(ctx):
    await ctx.channel.trigger_typing()
    roles_to_add = []
    existing_kamioshi_roles = [r for r in ctx.author.roles if r.id in hkd.WUG_KAMIOSHI_ROLE_IDS.values()]
    kamioshi_role_name = existing_kamioshi_roles[0].name if existing_kamioshi_roles else ''
    for oshi in hkd.WUG_ROLE_IDS:
        role = discord.utils.get(ctx.guild.roles, id=hkd.WUG_ROLE_IDS[oshi])
        if role not in ctx.author.roles and role.name != kamioshi_role_name:
            roles_to_add.append(role)
    if len(roles_to_add) > 0:
        await ctx.author.add_roles(*roles_to_add)
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you now have every WUG member role.'.format(ctx), colour=discord.Colour.teal()))
    else:
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have every WUG member role.'.format(ctx), colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def kamioshi(ctx, member: str=''):
    await ctx.channel.trigger_typing()
    role = get_wug_role(ctx.guild, member)
    if role is None:
        await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=discord.Colour.red()))
        return
    roles_to_remove = []
    if role in ctx.author.roles:
        roles_to_remove.append(role)
    kamioshi_role = hkd.get_kamioshi_role(ctx.guild, member)
    for existing_role in ctx.author.roles:
        if existing_role.id != kamioshi_role.id and existing_role.id in hkd.WUG_KAMIOSHI_ROLE_IDS.values():
            roles_to_remove.append(existing_role)
            ids_to_kamioshi = dict_reverse(hkd.WUG_KAMIOSHI_ROLE_IDS)
            replacement_role = discord.utils.get(ctx.guild.roles, id=hkd.WUG_ROLE_IDS[ids_to_kamioshi[existing_role.id]])
            await ctx.author.add_roles(replacement_role)
    if roles_to_remove:
        await ctx.author.remove_roles(*roles_to_remove)
        await asyncio.sleep(1)
    if kamioshi_role not in ctx.author.roles:
        await ctx.author.add_roles(kamioshi_role)
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you have set **{1}** as your kamioshi.'.format(ctx, member.title()), colour=kamioshi_role.colour))
    else:
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, that member is already your kamioshi.'.format(ctx), colour=discord.Colour.red()))

@bot.command(name='kamioshi-count', aliases=['kamioshicount'])
@commands.guild_only()
async def kamioshi_count(ctx):
    await ctx.channel.trigger_typing()
    ids_to_kamioshi = dict_reverse(hkd.WUG_KAMIOSHI_ROLE_IDS)
    oshi_num = {}
    for member in ctx.guild.members:
        kamioshi_roles = [r for r in member.roles if r.id in ids_to_kamioshi]
        if kamioshi_roles:
            kamioshi_role = kamioshi_roles[0]
            oshi_num[ids_to_kamioshi[kamioshi_role.id]] = oshi_num.get(ids_to_kamioshi[kamioshi_role.id], 0) + 1
        else:
            ids_to_member = dict_reverse(hkd.WUG_ROLE_IDS)
            member_roles = [r for r in member.roles if r.id in ids_to_member]
            if member_roles:
                role = sorted(member_roles)[-1]
                oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1
    description = ''
    for oshi in sorted(oshi_num.items(), key=itemgetter(1), reverse=True):
        description += '**{0}** ({1.mention}) - {2}\n'.format(oshi[0].title(), get_wug_role(ctx.guild, oshi[0]), oshi[1])
    await ctx.send(content='**Number of Users with Each WUG Member Role as Their Highest Role**', embed=create_embed(description=description))

@bot.command(name='oshi-count', aliases=['oshicount'])
@commands.guild_only()
async def oshi_count(ctx):
    await ctx.channel.trigger_typing()
    ids_to_member = dict_reverse(hkd.WUG_ROLE_IDS)
    ids_to_kamioshi = dict_reverse(hkd.WUG_KAMIOSHI_ROLE_IDS)
    oshi_num = {}
    for member in ctx.guild.members:
        counted_members = []
        for role in member.roles:
            if role.id in ids_to_member:
                cur_member = ids_to_member[role.id]
                if cur_member not in counted_members:
                    oshi_num[cur_member] = oshi_num.get(cur_member, 0) + 1
                    counted_members.append(cur_member)
            elif role.id in ids_to_kamioshi:
                cur_kamioshi = ids_to_kamioshi[role.id]
                if cur_kamioshi not in counted_members:
                    oshi_num[cur_kamioshi] = oshi_num.get(cur_kamioshi, 0) + 1
                    counted_members.append(cur_kamioshi)
    description = ''
    for oshi in sorted(oshi_num.items(), key=itemgetter(1), reverse=True):
        description += '**{0}** ({1.mention}) - {2}\n'.format(oshi[0].title(), get_wug_role(ctx.guild, oshi[0]), oshi[1])
    await ctx.send(content='**Number of Users with Each WUG Member Role**', embed=create_embed(description=description))

@bot.command()
@commands.guild_only()
async def events(ctx, *, date: str=''):
    await ctx.channel.trigger_typing()
    event_urls = []
    current_time = datetime.now(pytz.timezone('Japan'))
    search_date = parser.parse(date) if date else current_time
    if current_time.month > search_date.month or current_time.month == search_date.month and current_time.day > search_date.day:
        search_year = current_time.year + 1
    else:
        search_year = current_time.year
    first = True
    for _ in range(3):
        with suppress(Exception):
            soup = get_html_from_url('https://www.eventernote.com/events/month/{0}-{1}-{2}/1?limit=1000'.format(search_year, search_date.month, search_date.day))
            result = soup.find_all(attrs={ 'class': ['date', 'event', 'actor', 'note_count'] })
            for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                info = event[1].find_all('a')
                event_time = event[1].find('span')
                event_url = info[0]['href']
                if event_url not in event_urls:
                    performers = [p.contents[0] for p in event[2].find_all('a')]
                    wug_performers = [p for p in performers if p in hkd.WUG_MEMBERS]
                    if not wug_performers:
                        continue
                    await ctx.channel.trigger_typing()
                    colour = get_oshi_colour(ctx.guild, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]) if len(wug_performers) == 1 else discord.Colour.teal()
                    if first:
                        first = False
                        await ctx.send('**Events Involving WUG Members on {0:%Y}-{0:%m}-{0:%d} ({0:%A})**'.format(search_date.replace(year=search_year)))
                        await ctx.channel.trigger_typing()
                        await asyncio.sleep(0.5)
                    other_performers = [p for p in performers if p not in hkd.WUG_MEMBERS and p not in hkd.WUG_OTHER_UNITS]
                    embed_fields = []
                    embed_fields.append(('Location', info[1].contents[0]))
                    embed_fields.append(('Time', event_time.contents[0] if event_time else 'To be announced'))
                    embed_fields.append(('WUG Members', ', '.join(wug_performers)))
                    embed_fields.append(('Other Performers', ', '.join(other_performers) if other_performers else 'None'))
                    embed_fields.append(('Eventernote Attendees', event[3].find('p').contents[0]))
                    event_urls.append(event_url)
                    await asyncio.sleep(0.5)
                    await ctx.send(embed=create_embed(title=info[0].contents[0], colour=colour, url='https://www.eventernote.com{0}'.format(event_url), thumbnail=event[0].find('img')['src'], fields=embed_fields, inline=True))
            break
    if not event_urls:
        await ctx.send(embed=create_embed(description="Couldn't find any events on that day.", colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def eventsin(ctx, month: str, member: str=''):
    await ctx.channel.trigger_typing()
    search_month = hkd.parse_month(month)
    if search_month == 'None':
        await ctx.send(embed=create_embed(description="Couldn't find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.", colour=discord.Colour.red()))
        return
    current_time = datetime.now(pytz.timezone('Japan'))
    search_year = str(current_time.year if current_time.month <= int(search_month) else current_time.year + 1)
    search_index = [0]
    wug_names = list(hkd.WUG_ROLE_IDS.keys())
    if member:
        if parse_oshi_name(member) not in wug_names:
            await ctx.send(embed=create_embed(description="Couldn't find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.", colour=discord.Colour.red()))
            return
        search_index = [wug_names.index(parse_oshi_name(member)) + 1]
    event_urls = []
    first = True
    search_start = False
    for i in search_index:
        for _ in range(3):
            with suppress(Exception):
                soup = get_html_from_url('https://www.eventernote.com/actors/{0}/{1}/events?actor_id={1}&limit=5000'.format(quote(hkd.WUG_MEMBERS[i]), hkd.WUG_EVENTERNOTE_IDS[i]))
                result = soup.find_all(attrs={ 'class': ['date', 'event', 'actor', 'note_count'] })
                events = []
                for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                    event_date = event[0].find('p').contents[0][:10]
                    if event_date[:4] == search_year and event_date[5:7] == search_month:
                        search_start = True
                        events.append(event)
                    elif search_start:
                        break
                    else:
                        continue
                for event in reversed(events):
                    info = event[1].find_all('a')
                    event_date = event[0].find('p').contents[0][:10]
                    event_time = event[1].find('span')
                    event_url = info[0]['href']
                    if event_url not in event_urls:
                        performers = [p.contents[0] for p in event[2].find_all('a')]
                        wug_performers = [p for p in performers if p in hkd.WUG_MEMBERS]
                        if not wug_performers:
                            continue
                        await ctx.channel.trigger_typing()
                        colour = get_oshi_colour(ctx.guild, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]) if len(wug_performers) == 1 else discord.Colour.teal()
                        if first:
                            first = False
                            await ctx.send('**Events for {0} in {1} {2}**'.format(member.title() if member else 'Wake Up, Girls!', month_name[int(search_month)], search_year))
                            await asyncio.sleep(0.5)
                        other_performers = [p for p in performers if p not in hkd.WUG_MEMBERS and p not in hkd.WUG_OTHER_UNITS]
                        embed_fields = []
                        embed_fields.append(('Location', info[1].contents[0]))
                        embed_fields.append(('Date', '{0} ({1:%A})'.format(event_date, parser.parse(event_date))))
                        embed_fields.append(('Time', event_time.contents[0] if event_time else 'To be announced'))
                        embed_fields.append(('WUG Members', ', '.join(wug_performers)))
                        embed_fields.append(('Other Performers', ', '.join(other_performers) if other_performers else 'None'))
                        embed_fields.append(('Eventernote Attendees', event[3].find('p').contents[0]))
                        event_urls.append(event_url)
                        await asyncio.sleep(0.5)
                        await ctx.send(embed=create_embed(title=info[0].contents[0], colour=colour, url='https://www.eventernote.com{0}'.format(event_url), thumbnail=event[0].find('img')['src'], fields=embed_fields, inline=True))
                break
    if not event_urls:
        await ctx.send(embed=create_embed(description="Couldn't find any events during that month.", colour=discord.Colour.red()))

@bot.command(aliases=['createtag'])
@commands.guild_only()
async def tagcreate(ctx, *, tag_to_create: str):
    await ctx.channel.trigger_typing()
    split_request = tag_to_create.split()
    if len(split_request) > 1:
        tag_name = split_request[0]
        tag_content = tag_to_create[len(tag_name) + 1:]
        if tag_name not in firebase_ref.child('tags').get():
            firebase_ref.child('tags/{0}'.format(tag_name)).set(tag_content)
            await ctx.send(embed=create_embed(title='Successfully created tag - {0}'.format(tag_name)))
        else:
            await ctx.send(embed=create_embed(title='That tag already exists. Please choose a different tag name.', colour=discord.Colour.red()))
        return
    await ctx.send(embed=create_embed(description="Couldn't create tag. Please follow this format for creating a tag: **!tagcreate** *NameOfTag* *Content of the tag*.", colour=discord.Colour.red()))

@bot.command(aliases=['updatetag'])
@commands.guild_only()
async def tagupdate(ctx, *, tag_to_update: str):
    await ctx.channel.trigger_typing()
    split_update = tag_to_update.split()
    if len(split_update) > 1:
        tag_name = split_update[0]
        updated_content = tag_to_update[len(tag_name) + 1:]
        if tag_name in firebase_ref.child('tags').get():
            firebase_ref.child('tags/{0}'.format(tag_name)).set(updated_content)
            await ctx.send(embed=create_embed(title='Successfully updated tag - {0}.'.format(tag_name)))
        else:
            await ctx.send(embed=create_embed(title="That tag doesn't exist.".format(tag_name)))
        return
    await ctx.send(embed=create_embed(description="Couldn't update tag. Please follow this format for updating a tag: **!tagupdate** *NameOfTag* *Updated content of the tag*.", colour=discord.Colour.red()))

@bot.command(aliases=['tagremove', 'deletetag', 'removetag'])
@commands.guild_only()
async def tagdelete(ctx, tag_name: str):
    await ctx.channel.trigger_typing()
    if firebase_ref.child('tags/{0}'.format(tag_name)).get():
        firebase_ref.child('tags/{0}'.format(tag_name)).delete()
        await ctx.send(embed=create_embed(title='Successfully removed tag - {0}.'.format(tag_name)))
    else:
        await ctx.send(embed=create_embed(title="That tag doesn't exist.", colour=discord.Colour.red()))

@bot.command(aliases=['searchtag', 'tags'])
@commands.guild_only()
async def tagsearch(ctx):
    await ctx.channel.trigger_typing()
    tag_list = firebase_ref.child('tags').get()
    await ctx.send(content='Existing Tags', embed=create_embed(title=', '.join(list(tag_list.keys()))))

@bot.command()
@commands.guild_only()
async def tag(ctx, tag_name: str):
    await ctx.channel.trigger_typing()
    tag_result = firebase_ref.child('tags/{0}'.format(tag_name)).get()
    if tag_result:
        split_tag = hkd.split_embeddable_content(tag_result)
        if not split_tag:
            await ctx.send(tag_result)
        else:
            for link in split_tag:
                await ctx.channel.trigger_typing()
                await asyncio.sleep(1)
                await ctx.send(link)
    else:
        await ctx.send(embed=create_embed(description="That tag doesn't exist. Use **!tagcreate** *tag_name* *Content of the tag* to create a tag.", colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def vote(ctx, option: int):
    if not poll.options:
        await ctx.send(embed=create_embed(title='There is no currently ongoing poll.', colour=discord.Colour.red()))
        return
    if option > len(poll.options):
        await ctx.send(embed=create_embed(title='The currently running poll does not have that many options. Use **!polldetails** to see the options.', colour=discord.Colour.red()))
        return
    poll.vote(option, ctx.author.id)

@bot.command(aliases=['user-info'])
@commands.guild_only()
async def userinfo(ctx, member: discord.Member=None):
    await ctx.channel.trigger_typing()
    user = member or ctx.author
    embed_fields = []
    embed_fields.append(('Name', '{0}'.format(user.display_name)))
    embed_fields.append(('ID', '{0}'.format(user.id)))
    embed_fields.append(('Joined Server', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(user.joined_at)))
    embed_fields.append(('Account Created', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(user.created_at)))
    embed_fields.append(('Roles', '{0}'.format(', '.join([r.name for r in user.roles[1:]]) if len(user.roles[1:]) > 0 else 'None')))
    embed_fields.append(('Avatar', '{0}'.format('<{0}>'.format(user.avatar_url) if user.avatar_url else 'None')))
    await ctx.send(content='**User Information for {0.mention}**'.format(user), embed=create_embed(fields=embed_fields, inline=True))

@bot.command(aliases=['server-info'])
@commands.guild_only()
async def serverinfo(ctx):
    await ctx.channel.trigger_typing()
    guild = ctx.guild
    embed_fields = []
    embed_fields.append(('{0}'.format(guild.name), '(ID: {0})'.format(guild.id)))
    embed_fields.append(('Owner', '{0} (ID: {1})'.format(guild.owner, guild.owner.id)))
    embed_fields.append(('Members', '{0}'.format(guild.member_count)))
    embed_fields.append(('Channels', '{0} text, {1} voice'.format(len(guild.text_channels), len(guild.voice_channels))))
    embed_fields.append(('Roles', '{0}'.format(len(guild.roles))))
    embed_fields.append(('Created On', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(guild.created_at)))
    embed_fields.append(('Region', '{0}'.format(guild.region)))
    embed_fields.append(('Icon', '{0}'.format('<{0}>'.format(guild.icon_url) if guild.icon_url else 'None')))
    await ctx.send(content='**Server Information**', embed=create_embed(fields=embed_fields, inline=True))

@bot.command()
async def mv(ctx, *, song_name: str):
    await ctx.channel.trigger_typing()
    name_to_mv = {}
    for mv, names in list(firebase_ref.child('music_videos/mv_aliases').get().items()):
        name_to_mv.update({name: mv for name in names})
    song = hkd.parse_mv_name(song_name)
    if song in name_to_mv:
        await ctx.send(firebase_ref.child('music_videos/mv_links').get()[name_to_mv[song]])
    else:
        await ctx.send(embed=create_embed(description="Couldn't find that MV. Use **!mv-list** to show the list of available MVs.", colour=discord.Colour.red()))

@bot.command(name='mv-list', aliases=['mvlist', 'mvs'])
async def mv_list(ctx):
    await ctx.channel.trigger_typing()
    description = '{0}\n\n'.format('\n'.join(list(firebase_ref.child('music_videos/mv_links').get().keys())))
    description += 'Use **!mv** *song* to show the full MV. You can also write the name of the song in English.'
    await ctx.send(content='**List of Available Music Videos**', embed=create_embed(description=description))

@bot.command(name='aichan-blogpics')
@commands.cooldown(1, 10, BucketType.guild)
async def aichan_blogpics(ctx):
    await ctx.channel.trigger_typing()
    for _ in range(3):
        with suppress(Exception):
            soup = get_html_from_url('https://ameblo.jp/eino-airi/')
            blog_entry = soup.find_all(attrs={ 'class': 'skin-entryBody' }, limit=1)[0]
            pics = [p['href'] for p in blog_entry.find_all('a') if hkd.is_image_file(p['href'])]
            for pic in pics:
                await ctx.channel.trigger_typing()
                await asyncio.sleep(1)
                await ctx.send(pic)
            if not pics:
                await ctx.send(embed=create_embed(description="Couldn't find any pictures.", colour=discord.Colour.red()))
            break

@bot.command(name='seiyuu-vids', aliases=['seiyuuvids'])
async def seiyuu_vids(ctx):
    await ctx.channel.trigger_typing()
    await ctx.send(content='**WUG Seiyuu Videos**', embed=create_embed(title='List of seiyuu content on the Wake Up, Girls! wiki', url='http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content'))

@bot.command(aliases=['translate'])
async def tl(ctx, *, text: str):
    await ctx.channel.trigger_typing()
    await ctx.send(embed=create_embed(description=Translator().translate(text, src='ja', dest='en').text))

@bot.command(aliases=['convert'])
async def currency(ctx, *conversion: str):
    await ctx.channel.trigger_typing()
    if len(conversion) == 4 and conversion[2].lower() == 'to':
        with suppress(Exception):
            result = CurrencyRates().convert(conversion[1].upper(), conversion[3].upper(), Decimal(conversion[0]))
            await ctx.send(embed=create_embed(title='{0} {1}'.format('{:f}'.format(result).rstrip('0').rstrip('.'), conversion[3].upper())))
            return
    await ctx.send(embed=create_embed(description="Couldn't convert. Please follow this format for converting currency: **!currency** 12.34 AUD to USD.", colour=discord.Colour.red()))

@bot.command()
async def weather(ctx, *, location: str):
    await ctx.channel.trigger_typing()
    query = location.split(',')
    if len(query) > 1:
        with suppress(Exception):
            query[1] = pycountry.countries.get(name=query[1].strip().title()).alpha_2
    with suppress(Exception):
        result = requests.get('http://api.openweathermap.org/data/2.5/weather', params={ 'q': ','.join(query), 'APPID': config['weather_api_key'] }).json()
        timezone = pytz.timezone(TimezoneFinder().timezone_at(lat=result['coord']['lat'], lng=result['coord']['lon']))
        embed_fields = []
        embed_fields.append(('Weather', '{0}'.format(result['weather'][0]['description'].title())))
        embed_fields.append(('Temperature', '{0} °C, {1} °F'.format('{0:.2f}'.format(float(result['main']['temp']) - 273.15), '{0:.2f}'.format((1.8 * (float(result['main']['temp']) - 273.15)) + 32.0))))
        embed_fields.append(('Humidity', '{0}%'.format(result['main']['humidity'])))
        embed_fields.append(('Wind Speed', '{0} m/s'.format(result['wind']['speed'])))
        embed_fields.append(('Sunrise', '{0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunrise'], tz=timezone))))
        embed_fields.append(('Sunset', '{0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunset'], tz=timezone))))
        embed_fields.append(('Pressure', '{0} hPa'.format(result['main']['pressure'])))
        await ctx.send(content='**Weather for {0}, {1}**'.format(result['name'], pycountry.countries.lookup(result['sys']['country']).name), embed=create_embed(fields=embed_fields, inline=True))
        return
    await ctx.send(embed=create_embed(description="Couldn't get weather. Please follow this format for checking the weather: **!weather** Melbourne, Australia.", colour=discord.Colour.red()))

@bot.command(aliases=['pick'])
async def choose(ctx, *options: str):
    await ctx.channel.trigger_typing()
    if len(options) > 1:
        await ctx.send(embed=create_embed(description=options[randrange(len(options))]))
    else:
        await ctx.send(embed=create_embed(description='Please provide 2 or more options to choose from, e.g. **!choose** *option1* *option2*.', colour=discord.Colour.red()))

@bot.command(aliases=['youtube', 'play'])
async def yt(ctx, *, query: str):
    await ctx.channel.trigger_typing()
    for _ in range(3):
        with suppress(Exception):
            soup = get_html_from_url('https://www.youtube.com/results?search_query={0}'.format(quote(query)))
            for result in soup.find_all(attrs={ 'class': 'yt-uix-tile-link' }):
                link = result['href']
                if hkd.is_youtube_link(link):
                    await ctx.send('https://www.youtube.com{0}'.format(link))
                    return
            break
    await ctx.send(embed=create_embed(title="Couldn't find any results.", colour=discord.Colour.red()))

@bot.command(name='dl-vid', aliases=['dlvid', 'youtube-dl', 'ytdl'])
@commands.guild_only()
async def dl_vid(ctx, url: str):
    await ctx.channel.trigger_typing()
    await ctx.send('Attempting to download the video using youtube-dl. Please wait.')
    niconico_vid = 'nicovideo.jp' in url
    ytdl_getfilename_args = ['youtube-dl']
    if niconico_vid:
        ytdl_getfilename_args += ['-u', config['nicovideo_user'], '-p', config['nicovideo_pw']]
    ytdl_getfilename_args += ['--get-filename', url]
    proc = subprocess.run(args=ytdl_getfilename_args, universal_newlines=True, stdout=subprocess.PIPE)
    vid_filename = proc.stdout.strip()
    ytdl_args = ['youtube-dl', '-o', vid_filename, '-f', 'best']
    if niconico_vid:
        ytdl_args += ['-u', config['nicovideo_user'], '-p', config['nicovideo_pw']]
    ytdl_args.append(url)
    last_try_time = time.time()
    retry = True
    while retry:
        proc = subprocess.Popen(args=ytdl_args)
        while proc.poll() is None:
            await asyncio.sleep(2)
        if proc.returncode != 0:
            if niconico_vid and time.time() - last_try_time > 30:
                last_try_time = time.time()
                continue
            else:
                await ctx.send(embed=create_embed(title='Failed to download video.', colour=discord.Colour.red()))
                with suppress(Exception):
                    os.remove('{0}.part'.format(vid_filename))
                return
        retry = False
    await ctx.send('Download complete. Now uploading video to Google Drive. Please wait.')
    proc = subprocess.Popen(args=['python', 'gdrive_upload.py', vid_filename, config['uploads_folder']])
    while proc.poll() is None:
        await asyncio.sleep(1)
    if proc.returncode != 0:
        await ctx.send(embed=create_embed(title='Failed to upload video to Google Drive.', colour=discord.Colour.red()))
        with suppress(Exception):
            os.remove(vid_filename)
        return
    await ctx.send(content='{0.mention}'.format(ctx.author), embed=create_embed(description='Upload complete. Your video is available here: https://drive.google.com/open?id={0}. The Google Drive folder has limited space so it will be purged from time to time.'.format(config['uploads_folder'])))

@bot.command(aliases=['onsenmusume'])
async def onmusu(ctx, member: str=''):
    char, char_colour = hkd.WUG_ONMUSU_CHARS[parse_oshi_name(member)]
    await ctx.channel.trigger_typing()
    profile_link = 'https://onsen-musume.jp/character/{0}'.format(char)
    soup = get_html_from_url(profile_link)
    char_pic = 'https://onsen-musume.jp{0}'.format(soup.find('div', class_='character_ph__main').find('img')['src'])
    serifu = soup.find('div', class_='character_ph__serif').find('img')['alt']
    char_main = soup.find('div', class_='character_post__main')
    char_name = char_main.find('img')['alt']
    seiyuu = char_main.find('h2').find('img')['alt'][3:7]
    char_catch = char_main.find('p', class_='character_post__catch').contents[0]
    embed_fields = []
    for item in char_main.find('ul', class_='character_profile').find_all('li'):
        for i, entry in enumerate(item.find_all('span')):
            embed_fields.append((entry.contents[0], item.contents[(i + 1) * 2][1:]))
    soup = get_html_from_url('https://onsen-musume.jp/character/')
    thumbnail = 'https://onsen-musume.jp{0}'.format(soup.find('li', class_='character-list__item02 {0}'.format(char)).find('img')['src'])
    author = {}
    author['name'] = char_name
    author['url'] = profile_link
    author['icon_url'] = 'https://onsen-musume.jp/wp/wp-content/themes/onsenmusume/pc/assets/img/character/thumb/list/yu_icon.png'
    footer = {}
    footer['text'] = serifu
    await ctx.send(embed=create_embed(author=author, title='CV: {0}'.format(seiyuu), description=char_catch, colour=discord.Colour(char_colour), image=char_pic, thumbnail=thumbnail, fields=embed_fields, footer=footer, inline=True))

@bot.command()
async def say(ctx, channel_name: str, *, message: str):
    if ctx.author.id != hkd.BOT_ADMIN_ID:
        return
    guild = discord.utils.get(bot.guilds, id=hkd.SERVER_ID)
    channel = discord.utils.get(guild.channels, name=channel_name)
    await channel.trigger_typing()
    await asyncio.sleep(1.5)
    await channel.send(message)

bot.loop.create_task(check_mute_status())
bot.loop.create_task(check_tweets())
bot.loop.create_task(check_instagram())
bot.loop.create_task(check_instagram_stories())
bot.loop.create_task(check_live_streams())
bot.run(config['token'])