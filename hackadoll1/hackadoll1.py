import asyncio, discord, os, pycountry, pytz, requests, subprocess, time, twitter
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
from hkdhelper import create_embed, get_muted_role, get_wug_role, parse_oshi_name
from html import unescape
from httplib2 import Http
from humanfriendly import format_timespan
from oauth2client import file
from operator import itemgetter
from random import randrange
from timezonefinder import TimezoneFinder
from urllib.parse import quote
from urllib.request import urlopen

config = hkd.parse_config()
bot = commands.Bot(command_prefix=('!', 'ichigo ', 'alexa ', 'Ichigo ', 'Alexa '))
bot.remove_command('help')
certificate = credentials.Certificate(config['firebase_credentials'])
firebase = initialize_app(certificate, { 'databaseURL': config['firebase_db'] })
firebase_ref = db.reference()
muted_members = firebase_ref.child('muted_members').get() or {}
twitter_api = twitter.Api(consumer_key=config['consumer_key'], consumer_secret=config['consumer_secret'], access_token_key=config['access_token_key'], access_token_secret=config['access_token_secret'], tweet_mode='extended')
poll = hkd.Poll()
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
                guild = discord.utils.get(bot.guilds, id=hkd.SERVER_ID)
                member = discord.utils.get(guild.members, id=int(member_id))
                await member.remove_roles(get_muted_role(guild))
        for member_id in members_to_unmute:
            muted_members.pop(member_id)
        await asyncio.sleep(30)

@bot.event
async def check_tweets():
    await bot.wait_until_ready()
    while not bot.is_closed():
        guild = discord.utils.get(bot.guilds, id=hkd.SERVER_ID)
        channel = discord.utils.get(guild.channels, id=hkd.TWITTER_CHANNEL_ID)
        for _ in range(3):
            with suppress(Exception):
                for name in firebase_ref.child('last_tweet_ids').get().keys():
                    last_tweet_id = int(firebase_ref.child('last_tweet_ids/{0}'.format(name)).get())
                    posted_tweets = []
                    for status in twitter_api.GetUserTimeline(screen_name=name, since_id=last_tweet_id, count=40, include_rts=False):
                        tweet = status.AsDict()
                        if tweet.get('in_reply_to_screen_name', name) != name:
                            continue
                        await channel.trigger_typing()
                        await asyncio.sleep(1)
                        tweet_id = tweet['id']
                        posted_tweets.append(tweet_id)
                        user = tweet['user']
                        tweet_content = unescape(tweet['full_text'])
                        role = None
                        if '公式ブログを更新しました' in tweet_content:
                            for i, sign in enumerate(hkd.WUG_TWITTER_BLOG_SIGNS):
                                if sign in tweet_content:
                                    role = get_wug_role(guild, list(hkd.WUG_ROLE_IDS.keys())[i])
                        colour = role.colour if role else discord.Colour.light_grey()
                        author = {}
                        author['name'] = '{0} (@{1})'.format(user['name'], user['screen_name'])
                        author['url'] = 'https://twitter.com/{0}'.format(name)
                        author['icon_url'] = user['profile_image_url_https']
                        image = ''
                        media = tweet.get('media', '')
                        if media:
                            image = media[0].get('media_url_https', '')
                        if role:
                            html_response = urlopen('https://ameblo.jp/wakeupgirls/')
                            soup = BeautifulSoup(html_response, 'html.parser')
                            blog_entry = soup.find(attrs={ 'class': 'skin-entryBody' })
                            blog_images = [p['src'] for p in blog_entry.find_all('img') if '?caw=' in p['src'][-9:]]
                            if blog_images:
                                image = blog_images[-1]
                        await channel.send(embed=create_embed(author=author, title='Tweet by {0}'.format(user['name']), description=tweet_content, colour=colour, url='https://twitter.com/{0}/status/{1}'.format(name, tweet_id), image=image))
                    if posted_tweets:
                        firebase_ref.child('last_tweet_ids/{0}'.format(name)).set(str(max(posted_tweets)))
                break
        await asyncio.sleep(20)

@bot.event
async def check_poll_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        topic, channel_id, results = poll.check_status()
        if channel_id:
            guild = discord.utils.get(bot.guilds, id=hkd.SERVER_ID)
            channel = discord.utils.get(guild.channels, id=channel_id)
            if topic:
                await channel.send(content='Poll ended.', embed=create_embed(title=topic, description=results))
            else:
                await channel.send(embed=create_embed(title='The creator of the poll took too long to specify the options. The poll has been cancelled.', colour=discord.Colour.red()))
        await asyncio.sleep(10)

@bot.event
async def check_wugch_omake():
    await bot.wait_until_ready()
    while not bot.is_closed():
        wugch_vid = ''
        for _ in range(3):
            with suppress(Exception):
                html_response = urlopen('http://ch.nicovideo.jp/WUGch/video')
                soup = BeautifulSoup(html_response, 'html.parser')
                for top_video in soup.find_all('h6', limit=2):
                    video = top_video.find('a')
                    if 'オマケ放送' in video['title']:
                        prev_wugch_omake = int(firebase_ref.child('last_wugch_omake').get())
                        latest_wugch_omake = int(video['href'][video['href'].rfind('/') + 1:])
                        if latest_wugch_omake > prev_wugch_omake:
                            wugch_vid = video['href']
                            break
                break
        if wugch_vid:
            vid_filename = '{0}.mp4'.format(video['title'])
            last_try_time = time.time()
            retry = True
            while retry:
                proc = subprocess.Popen(args=['youtube-dl', '-o', vid_filename, '-f', 'best', '-u', config['nicovideo_user'], '-p', config['nicovideo_pw'], wugch_vid])
                while proc.poll() is None:
                    await asyncio.sleep(2)
                if proc.returncode != 0:
                    if time.time() - last_try_time > 30:
                        last_try_time = time.time()
                        continue
                retry = False
            proc = subprocess.Popen(args=['python', 'gdrive_upload.py', vid_filename, config['wugch_folder']])
            while proc.poll() is None:
                await asyncio.sleep(1)
            if proc.returncode != 0:
                with suppress(Exception):
                    os.remove(vid_filename)
            else:
                firebase_ref.child('last_wugch_omake').set(str(latest_wugch_omake))
                guild = discord.utils.get(bot.guilds, id=hkd.SERVER_ID)
                channel = discord.utils.get(guild.channels, id=hkd.SEIYUU_CHANNEL_ID)
                await channel.send(embed=create_embed(description='{0} is now available for download at https://drive.google.com/open?id={1}'.format(video['title'], config['wugch_folder'])))
        await asyncio.sleep(1800)

@bot.event
async def check_live_streams():
    await bot.wait_until_ready()
    while not bot.is_closed():
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
                        guild = discord.utils.get(bot.guilds, id=hkd.SERVER_ID)
                        channel = discord.utils.get(guild.channels, id=hkd.SEIYUU_CHANNEL_ID)
                        colour = get_wug_role(guild, wug_members[0]).colour if len(wug_members) == 1 else discord.Colour.teal()
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
        embed_fields.append(('!help polls', 'Show help for poll commands.'))
        embed_fields.append(('!mv *song*', 'Show full MV of a song.'))
        embed_fields.append(('!mv-list', 'Show list of available MVs.'))
        embed_fields.append(('!userinfo', 'Show your user information.'))
        embed_fields.append(('!serverinfo', 'Show server information.'))
        embed_fields.append(('!blogpics *member*', 'Get pictures from the latest blog post of the specified WUG member (optional). If *member* not specified, gets pictures from the latest blog post.'))
        embed_fields.append(('!seiyuu-vids', 'Show link to the wiki page with WUG seiyuu content.'))
        embed_fields.append(('!wugch-omake', 'Show link to the Google Drive folder with WUG Channel omake videos.'))
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
    description += '\nNote that using **!oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **!oshimashi** *member* instead. To get all 7 roles, use **!hakooshi**.\n\n'
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

@help.command()
async def polls(ctx, aliases=['poll']):
    embed_fields = []
    embed_fields.append(('!pollcreate *duration* *topic*', 'Create a poll for the specified topic, lasting for *duration* minutes.'))
    embed_fields.append(('!polloptions *options*', 'Specify the options for a created poll.'))
    embed_fields.append(('!polldetails', 'See the options for the currently running poll.'))
    embed_fields.append(('!pollend', 'Immediately end an ongoing poll.'))
    embed_fields.append(('!vote *number*', 'Vote for an option in a poll.'))
    await ctx.send(content='**Commands for Making Polls**', embed=create_embed(fields=embed_fields))

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
async def oshihen(ctx, member: str):
    await ctx.channel.trigger_typing()
    role = get_wug_role(ctx.guild, parse_oshi_name(member))
    if role is None:
        await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=discord.Colour.red()))
        return
    roles_to_remove = []
    for existing_role in ctx.author.roles:
        if existing_role.id in hkd.WUG_ROLE_IDS.values():
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
async def oshimashi(ctx, member: str):
    await ctx.channel.trigger_typing()
    role = get_wug_role(ctx.guild, parse_oshi_name(member))
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
    for role in ctx.guild.roles:
        if role not in ctx.author.roles and role.id in hkd.WUG_ROLE_IDS.values():
            roles_to_add.append(role)
    if len(roles_to_add) > 0:
        await ctx.author.add_roles(*roles_to_add)
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you now have every WUG member role.'.format(ctx), colour=discord.Colour.teal()))
    else:
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have every WUG member role.'.format(ctx), colour=discord.Colour.red()))

@bot.command(name='kamioshi-count', aliases=['kamioshicount', 'kamioshi count'])
@commands.guild_only()
async def kamioshi_count(ctx):
    await ctx.channel.trigger_typing()
    ids_to_member = hkd.dict_reverse(hkd.WUG_ROLE_IDS)
    oshi_num = {}
    for member in ctx.guild.members:
        member_roles = [r for r in member.roles if r.id in ids_to_member]
        if len(member_roles) > 0:
            role = sorted(member_roles)[-1]
            oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1
    description = ''
    for oshi in sorted(oshi_num.items(), key=itemgetter(1), reverse=True):
        description += '**{0}** ({1.mention}) - {2}\n'.format(oshi[0].title(), get_wug_role(ctx.guild, oshi[0]), oshi[1])
    await ctx.send(content='**Number of Users with Each WUG Member Role as Their Highest Role**', embed=create_embed(description=description))

@bot.command(name='oshi-count', aliases=['oshicount', 'oshi count'])
@commands.guild_only()
async def oshi_count(ctx):
    await ctx.channel.trigger_typing()
    ids_to_member = hkd.dict_reverse(hkd.WUG_ROLE_IDS)
    oshi_num = {}
    for member in ctx.guild.members:
        for role in member.roles:
            if role.id in ids_to_member:
                oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1
    description = ''
    for oshi in sorted(oshi_num.items(), key=itemgetter(1), reverse=True):
        description += '**{0}** ({1.mention}) - {2}\n'.format(oshi[0].title(), get_wug_role(ctx.guild, oshi[0]), oshi[1])
    await ctx.send(content='**Number of Users with Each WUG Member Role**', embed=create_embed(description=description))

@bot.command()
@commands.guild_only()
async def events(ctx, *, date: str=''):
    await ctx.channel.trigger_typing()
    event_urls = []
    search_date = parser.parse(date) if date else datetime.now(pytz.timezone('Japan'))
    first = True
    for _ in range(3):
        with suppress(Exception):
            html_response = urlopen('https://www.eventernote.com/events/month/{0}-{1}-{2}/1?limit=1000'.format(search_date.year, search_date.month, search_date.day))
            soup = BeautifulSoup(html_response, 'html.parser')
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
                    colour = get_wug_role(ctx.guild, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]).colour if len(wug_performers) == 1 else discord.Colour.teal()
                    if first:
                        first = False
                        await ctx.send('**Events Involving WUG Members on {0:%Y}-{0:%m}-{0:%d} ({0:%A})**'.format(search_date))
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
        if member.lower() not in wug_names:
            await ctx.send(embed=create_embed(description="Couldn't find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.", colour=discord.Colour.red()))
            return
        search_index = [wug_names.index(member.lower()) + 1]
    event_urls = []
    first = True
    search_start = False
    for i in search_index:
        for _ in range(3):
            with suppress(Exception):
                html_response = urlopen('https://www.eventernote.com/actors/{0}/{1}/events?actor_id={1}&limit=5000'.format(quote(hkd.WUG_MEMBERS[i]), hkd.WUG_EVENTERNOTE_IDS[i]))
                soup = BeautifulSoup(html_response, 'html.parser')
                result = soup.find_all(attrs={ 'class': ['date', 'event', 'actor', 'note_count'] })
                for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                    event_date = event[0].find('p').contents[0][:10]
                    if event_date[:4] == search_year and event_date[5:7] == search_month:
                        search_start = True
                    elif search_start:
                        break
                    else:
                        continue
                    info = event[1].find_all('a')
                    event_time = event[1].find('span')
                    event_url = info[0]['href']
                    if event_url not in event_urls:
                        performers = [p.contents[0] for p in event[2].find_all('a')]
                        wug_performers = [p for p in performers if p in hkd.WUG_MEMBERS]
                        if not wug_performers:
                            continue
                        await ctx.channel.trigger_typing()
                        colour = get_wug_role(ctx.guild, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]).colour if len(wug_performers) == 1 else discord.Colour.teal()
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
            await asyncio.sleep(3)
            async for message in ctx.channel.history(after=ctx.message):
                if message.author == bot.user and not message.embeds:
                    if hkd.is_embeddable_content(message.content):
                        link_url = message.content
                        await message.edit(content='Reposting link...')
                        await asyncio.sleep(1)
                        await message.edit(content=link_url)
    else:
        await ctx.send(embed=create_embed(description="That tag doesn't exist. Use **!tagcreate** *tag_name* *Content of the tag* to create a tag.", colour=discord.Colour.red()))

@bot.command(aliases=['createpoll'])
@commands.guild_only()
async def pollcreate(ctx, duration: int, *, topic: str):
    await ctx.channel.trigger_typing()
    if duration > 120:
        await ctx.send(embed=create_embed(title='Please specify a duration of less than 2 hours.', colour=discord.Colour.red()))
        return
    elif duration < 1:
        await ctx.send(embed=create_embed(title='Please specify a duration of at least 1 minute.', colour=discord.COlour.red()))
        return
    if not poll.topic:
        poll.create(topic, ctx.author.id, duration, ctx.channel.id)
        await ctx.send(embed=create_embed(description='Poll successfully created. Please specify the options for the poll with **!polloptions** *options*, e.g. **!polloptions** first option, second option, third option.'))
    else:
        await ctx.send(embed=create_embed(description='There is already an ongoing poll. Please wait for the current poll to end, or if you are the creator of the current poll, you can end it with **!pollend**.', colour=discord.Colour.red()))

@bot.command()
@commands.guild_only()
async def polloptions(ctx, *, options: str):
    await ctx.channel.trigger_typing()
    if not poll.topic:
        await ctx.send(embed=create_embed(description='There is no created poll to provide options for. You can create a poll with **!pollcreate** *duration* *topic*.', colour=discord.Colour.red()))
        return
    if ctx.author.id != poll.owner:
        await ctx.send(embed=create_embed(title='Only the creator of the poll can specify the options.', colour=discord.Colour.red()))
        return
    if poll.options:
        await ctx.send(embed=create_embed(description='The options for this poll have already been specified. Please wait for the current poll to end, or if you are the creator of the current poll, you can end it with **!pollend**.', colour=discord.Colour.red()))
        return
    poll_options = [p.strip() for p in options.split(',')]
    if len(poll_options) < 2:
        await ctx.send(embed=create_embed(title='Please specify more than one option for the poll.', colour=discord.Colour.red()))
        return
    poll.set_options(poll_options, time.time() + poll.duration * 60)
    description = 'Vote for an option with **!vote** *number*, e.g. **!vote** 1 for option 1.\n\n'
    description += poll.get_details()
    await ctx.send(content='Poll created. This poll will last for {0}. The creator of the poll may end it early with **!pollend**.'.format(format_timespan(poll.duration * 60)), embed=create_embed(title=poll.topic, description=description))

@bot.command()
@commands.guild_only()
async def polldetails(ctx):
    await ctx.channel.trigger_typing()
    if not poll.options:
        await ctx.send(embed=create_embed(description='There is no poll currently ongoing. You can create a poll with **!pollcreate** *duration* *topic*.', colour=discord.Colour.red()))
        return
    description = 'Vote for an option with **!vote** *number*, e.g. **!vote** 1 for option 1.\n\n'
    description += poll.get_details()
    await ctx.send(content='Details of the currently running poll.', embed=create_embed(title=poll.topic, description=description))

@bot.command(aliases=['endpoll'])
@commands.guild_only()
async def pollend(ctx):
    await ctx.channel.trigger_typing()
    if not poll.topic:
        await ctx.send(embed=create_embed(description='There is no poll currently ongoing. You can create a poll with **!pollcreate** *duration* *topic*.', colour=discord.Colour.red()))
        return
    if not poll.options:
        await ctx.send(embed=create_embed(description='A poll was created but no options provided. The poll has been cancelled.'))
        return
    if ctx.author.id != poll.owner:
        await ctx.send(embed=create_embed(title='Only the creator of the poll can end it.', colour=discord.Colour.red()))
        return
    topic = poll.topic
    await ctx.send(content='Poll ended.', embed=create_embed(title=topic, description=poll.end()))

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
@commands.cooldown(1, 10, BucketType.guild)
async def blogpics(ctx, member: str=''):
    await ctx.channel.trigger_typing()
    for _ in range(3):
        with suppress(Exception):
            html_response = urlopen('https://ameblo.jp/wakeupgirls')
            soup = BeautifulSoup(html_response, 'html.parser')
            if member:
                blog_title = soup.find('h2')
                member_sign = blog_title.find('a').contents[0]
                day = -1
                for i, sign in enumerate(hkd.WUG_BLOG_ORDER):
                    if sign in member_sign:
                        day = i
                        if not member:
                            member = [m for m in hkd.WUG_BLOG_SIGNS.keys() if hkd.WUG_BLOG_SIGNS[m] == sign][0]
                if day == -1:
                    await ctx.send(embed=create_embed(description="Couldn't find pictures for that member.", colour=discord.Colour.red()))
                    return
                page, entry_num = map(sum, zip(divmod((hkd.WUG_BLOG_ORDER.index(hkd.WUG_BLOG_SIGNS[member.lower()]) - day) % 7, 3), (1, 1)))
            else:
                page = 1
                entry_num = 1
            if page != 1:
                html_response = urlopen('https://ameblo.jp/wakeupgirls/page-{0}.html'.format(page))
                soup = BeautifulSoup(html_response, 'html.parser')
            blog_entry = soup.find_all(attrs={ 'class': 'skin-entryBody' }, limit=entry_num)[entry_num - 1]
            pics = [p['href'] for p in blog_entry.find_all('a') if hkd.is_image_file(p['href'])]
            for pic in pics:
                await ctx.channel.trigger_typing()
                await asyncio.sleep(1)
                await ctx.send(pic)
            break
    if len(pics) == 0:
        await ctx.send(embed=create_embed(description="Couldn't find any pictures.", colour=discord.Colour.red()))
        return
    await asyncio.sleep(3)
    async for message in ctx.channel.history(after=ctx.message):
        if message.author == bot.user and hkd.is_image_file(message.content) and not message.embeds:
            image_url = message.content
            await message.edit(content='Reposting picture...')
            await asyncio.sleep(1)
            await message.edit(content=image_url)

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

@bot.command(name='mv-list', aliases=['mvlist'])
async def mv_list(ctx):
    await ctx.channel.trigger_typing()
    description = '{0}\n\n'.format('\n'.join(list(firebase_ref.child('music_videos/mv_links').get().keys())))
    description += 'Use **!mv** *song* to show the full MV. You can also write the name of the song in English.'
    await ctx.send(content='**List of Available Music Videos**', embed=create_embed(description=description))

@bot.command(name='seiyuu-vids', aliases=['seiyuuvids'])
async def seiyuu_vids(ctx):
    await ctx.channel.trigger_typing()
    await ctx.send(content='**WUG Seiyuu Videos**', embed=create_embed(title='List of seiyuu content on the Wake Up, Girls! wiki', url='http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content'))

@bot.command(name='wugch-omake', aliases=['wugch'])
@commands.guild_only()
async def wugch_omake(ctx):
    await ctx.channel.trigger_typing()
    await ctx.send(content='**WUG Channel Omake Videos**', embed=create_embed(title='Google Drive folder with recent WUGch omake videos', url='https://drive.google.com/open?id=1o0PWGdlCUhsIN72O0aKSP6HRbim5Fzpw'))

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
            html_response = urlopen('https://www.youtube.com/results?search_query={0}'.format(quote(query)))
            soup = BeautifulSoup(html_response, 'html.parser')
            for result in soup.find_all(attrs={ 'class': 'yt-uix-tile-link' }):
                link = result['href']
                if hkd.is_youtube_link(link):
                    await ctx.send('https://www.youtube.com{0}'.format(link))
                    return
            break
    await ctx.send(embed=create_embed(title="Couldn't find any results.", colour=discord.Colour.red()))

@bot.command(name='dl-vid', aliases=['dlvid', 'youtube-dl'])
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
            if niconico_vid:
                if time.time() - last_try_time > 30:
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

@bot.command()
async def onmusu(ctx, member: str=''):
    await ctx.channel.trigger_typing()
    char, char_colour = hkd.WUG_ONMUSU_CHARS[parse_oshi_name(member)]
    profile_link = 'https://onsen-musume.jp/character/{0}'.format(char)
    html_response = urlopen(profile_link)
    soup = BeautifulSoup(html_response, 'html.parser')
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
    html_response = urlopen('https://onsen-musume.jp/character/')
    soup = BeautifulSoup(html_response, 'html.parser')
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
bot.loop.create_task(check_poll_status())
bot.loop.create_task(check_wugch_omake())
bot.loop.create_task(check_live_streams())
bot.run(config['token'])