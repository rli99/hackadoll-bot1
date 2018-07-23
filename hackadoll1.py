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
from firebase_admin import credentials, db, initialize_app
from forex_python.converter import CurrencyRates
from googletrans import Translator
from hkdhelper import create_embed, get_muted_role, get_wug_role
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
bot = commands.Bot(command_prefix=('!', 'ichigo ', 'alexa '))
bot.remove_command('help')
certificate = credentials.Certificate(config['firebase_credentials'])
firebase = initialize_app(certificate, {'databaseURL': config['firebase_db']})
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
    while not bot.is_closed:
        members_to_unmute = []
        for member_id in muted_members:
            if time.time() > float(muted_members[member_id]):
                firebase_ref.child('muted_members/{0}'.format(member_id)).delete()
                members_to_unmute.append(member_id)
                server = discord.utils.get(bot.servers, id=hkd.SERVER_ID)
                member = discord.utils.get(server.members, id=member_id)
                await bot.remove_roles(member, get_muted_role(server))
        for member_id in members_to_unmute:
            muted_members.pop(member_id)
        await asyncio.sleep(30)

@bot.event
async def check_tweets():
    await bot.wait_until_ready()
    while not bot.is_closed:
        server = discord.utils.get(bot.servers, id=hkd.SERVER_ID)
        channel = discord.utils.get(server.channels, id=hkd.TWITTER_CHANNEL_ID)
        for _ in range(3):
            with suppress(Exception):
                for name in firebase_ref.child('last_tweet_ids').get().keys():
                    last_tweet_id = int(firebase_ref.child('last_tweet_ids/{0}'.format(name)).get())
                    posted_tweets = []
                    for status in twitter_api.GetUserTimeline(screen_name=name, since_id=last_tweet_id, count=40, include_rts=False, exclude_replies=True):
                        await bot.send_typing(channel)
                        await asyncio.sleep(1)
                        tweet = status.AsDict()
                        tweet_id = tweet['id']
                        posted_tweets.append(tweet_id)
                        user = tweet['user']
                        tweet_content = unescape(tweet['full_text'])
                        role = None
                        if '公式ブログを更新しました' in tweet_content:
                            for i, sign in enumerate(hkd.WUG_TWITTER_BLOG_SIGNS):
                                if sign in tweet_content:
                                    role = get_wug_role(server, list(hkd.WUG_ROLE_IDS.keys())[i])
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
                            blog_entry = soup.find(attrs={'class': 'skin-entryBody'})
                            blog_images = [p['src'] for p in blog_entry.find_all('img') if '?caw=' in p['src'][-9:]]
                            if blog_images:
                                image = blog_images[-1]
                        await bot.send_message(channel, embed=create_embed(author=author, title='Tweet by {0}'.format(user['name']), description=tweet_content, colour=colour, url='https://twitter.com/{0}/status/{1}'.format(name, tweet_id), image=image))
                    if posted_tweets:
                        firebase_ref.child('last_tweet_ids/{0}'.format(name)).set(str(max(posted_tweets)))
                break
        await asyncio.sleep(20)

@bot.event
async def check_poll_status():
    await bot.wait_until_ready()
    while not bot.is_closed:
        topic, channel_id, results = poll.check_status()
        if channel_id:
            server = discord.utils.get(bot.servers, id=hkd.SERVER_ID)
            channel = discord.utils.get(server.channels, id=channel_id)
            if topic:
                await bot.send_message(channel, content='Poll ended.', embed=create_embed(title=topic, description=results))
            else:
                await bot.send_message(channel, embed=create_embed(title='The creator of the poll took too long to specify the options. The poll has been cancelled.', colour=discord.Colour.red()))
        await asyncio.sleep(10)

@bot.event
async def check_wugch_omake():
    await bot.wait_until_ready()
    while not bot.is_closed:
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
                server = discord.utils.get(bot.servers, id=hkd.SERVER_ID)
                channel = discord.utils.get(server.channels, id=hkd.SEIYUU_CHANNEL_ID)
                await bot.send_message(channel, embed=create_embed(description='{0} is now available for download at https://drive.google.com/open?id={1}'.format(video['title'], config['wugch_folder'])))

        await asyncio.sleep(1800)

@bot.event
async def check_live_streams():
    await bot.wait_until_ready()
    while not bot.is_closed:
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
                        server = discord.utils.get(bot.servers, id=hkd.SERVER_ID)
                        channel = discord.utils.get(server.channels, id=hkd.SEIYUU_CHANNEL_ID)
                        colour = get_wug_role(server, wug_members[0]).colour if len(wug_members) == 1 else discord.Colour.teal()
                        embed_fields = []
                        embed_fields.append(('Time', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M} JST'.format(start.astimezone(pytz.timezone('Japan')))))
                        embed_fields.append(('WUG Members', ', '.join(wug_members)))
                        content = '**Starting in 15 Minutes**' if first_event else ''
                        await bot.send_message(channel, content=content, embed=create_embed(title=event['summary'], colour=colour, url=stream_link, fields=embed_fields))
                        first_event = False
                        event['description'] = '*' + event['description']
                        calendar.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
                break
        await asyncio.sleep(30)

@bot.group(pass_context=True)
async def help(ctx):
    await bot.send_typing(ctx.message.channel)
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
        await bot.say(content='**Available Commands**', embed=create_embed(fields=embed_fields))

@help.command(name='mod-commands')
async def mod_commands():
    embed_fields = []
    embed_fields.append(('!kick *member*', 'Kick a member.'))
    embed_fields.append(('!ban *member*', 'Ban a member.'))
    embed_fields.append(('!mute *member* *duration*', 'Mute a member for *duration* minutes.'))
    embed_fields.append(('!unmute *member*', 'Unmute a member.'))
    await bot.say(content='**Commands for Moderators**', embed=create_embed(fields=embed_fields))

@help.command(pass_context=True, no_pm=True)
async def roles(ctx):
    description = 'Users can have any of the 7 WUG member roles. Use **!oshihen** *member* to get the role you want.\n\n'
    for oshi in hkd.WUG_ROLE_IDS.keys():
        description += '**!oshihen** {0} for {1.mention}\n'.format(oshi.title(), get_wug_role(ctx.message.server, oshi))
    description += '\nNote that using **!oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **!oshimashi** *member* instead. To get all 7 roles, use **!hakooshi**.\n\n'
    description += 'Use **!oshi-count** to show the number of members with each WUG member role, or **!kamioshi-count** to show the number of members with each WUG member role as their highest role.\n'
    await bot.say(content='**Commands for Roles**', embed=create_embed(description=description))

@help.command()
async def events():
    embed_fields = []
    embed_fields.append(('!events *date*', 'Get information for events involving WUG members on the specified date, e.g. **!events** apr 1. If *date* not specified, finds events happening today.'))
    embed_fields.append(('!eventsin *month* *member*', 'Get information for events involving WUG members for the specified month and member, e.g. **!eventsin** April Mayushii. If *member* not specified, searches for Wake, Up Girls! related events instead. Searches events from this month onwards only.'))
    await bot.say(content='**Commands for Searching Events**', embed=create_embed(fields=embed_fields))

@help.command()
async def tags():
    embed_fields = []
    embed_fields.append(('!tagcreate *tag_name* *content*', 'Create a tag. Use one word (no spaces) for tag names.'))
    embed_fields.append(('!tagupdate *tag_name* *updated_content*', 'Update an existing tag.'))
    embed_fields.append(('!tagdelete *tag_name*', 'Delete an existing tag.'))
    embed_fields.append(('!tagsearch', 'Shows a list of all existing tags.'))
    embed_fields.append(('!tag *tag_name*', 'Display a saved tag.'))
    await bot.say(content='**Commands for Using Tags**', embed=create_embed(fields=embed_fields))

@help.command()
async def polls():
    embed_fields = []
    embed_fields.append(('!pollcreate *duration* *topic*', 'Create a poll for the specified topic, lasting for *duration* minutes.'))
    embed_fields.append(('!polloptions *options*', 'Specify the options for a created poll.'))
    embed_fields.append(('!polldetails', 'See the options for the currently running poll.'))
    embed_fields.append(('!pollend', 'Immediately end an ongoing poll.'))
    embed_fields.append(('!vote *number*', 'Vote for an option in a poll.'))
    await bot.say(content='**Commands for Making Polls**', embed=create_embed(fields=embed_fields))

@bot.command(pass_context=True, no_pm=True)
async def kick(ctx, member : discord.Member):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.kick_members:
        if member.server_permissions.administrator:
            await bot.say(embed=create_embed(title='Moderators cannot be kicked.', colour=discord.Colour.red()))
            return
        await bot.kick(member)
        await bot.say(embed=create_embed(title='{0} has been kicked.'.format(member)))
        firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        return
    await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def ban(ctx, member : discord.Member):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.ban_members:
        await bot.ban(member)
        await bot.say(embed=create_embed(title='{0} has been banned.'.format(member)))
        firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        return
    await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def mute(ctx, member : discord.Member, duration : int):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.kick_members:
        if member.server_permissions.administrator:
            await bot.say(embed=create_embed(title='Moderators cannot be muted.', colour=discord.Colour.red()))
            return
        if duration > 0:
            mute_endtime = time.time() + duration * 60
            firebase_ref.child('muted_members/{0}'.format(member.id)).set(str(mute_endtime))
            muted_members[member.id] = mute_endtime
            await bot.add_roles(member, get_muted_role(ctx.message.server))
            await bot.say(embed=create_embed(description='{0.mention} has been muted for {1}.'.format(member, format_timespan(duration * 60))))
        else:
            await bot.say(embed=create_embed(title='Please specify a duration greater than 0.', colour=discord.Colour.red()))
    else:
        await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def unmute(ctx, member : discord.Member):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.kick_members:
        firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        muted_members.pop(member.id)
        await bot.remove_roles(member, get_muted_role(ctx.message.server))
        await bot.say(embed=create_embed(description='{0.mention} has been unmuted.'.format(member)))
    else:
        await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def oshihen(ctx, member : str):
    await bot.send_typing(ctx.message.channel)
    role = get_wug_role(ctx.message.server, member)
    if role is None:
        await bot.say(embed=create_embed(description='Couldn\'t find that role. Use **!roles** to show additional help on how to get roles.', colour=discord.Colour.red()))
        return

    roles_to_remove = []
    for existing_role in ctx.message.author.roles:
        if existing_role.id in hkd.WUG_ROLE_IDS.values():
            roles_to_remove.append(existing_role)

    if len(roles_to_remove) == 1 and roles_to_remove[0].name == role.name:
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=discord.Colour.red()))
    elif len(roles_to_remove) > 0:
        await bot.remove_roles(ctx.message.author, *roles_to_remove)
        await asyncio.sleep(1)

    await bot.add_roles(ctx.message.author, role)
    await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you have oshihened to the **{1}** role {2.mention}.'.format(ctx, member.title(), role), colour=role.colour))

@bot.command(pass_context=True, no_pm=True)
async def oshimashi(ctx, member : str):
    await bot.send_typing(ctx.message.channel)
    role = get_wug_role(ctx.message.server, member)
    if role is None:
        await bot.say(embed=create_embed(description='Couldn\'t find that role. Use **!roles** to show additional help on how to get roles.', colour=discord.Colour.red()))
        return

    if role not in ctx.message.author.roles:
        await bot.add_roles(ctx.message.author, role)
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you now have the **{1}** oshi role {2.mention}.'.format(ctx, member.title(), role), colour=role.colour))
    else:
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def hakooshi(ctx):
    await bot.send_typing(ctx.message.channel)
    roles_to_add = []
    for role in ctx.message.server.roles:
        if role not in ctx.message.author.roles and role.id in hkd.WUG_ROLE_IDS.values():
            roles_to_add.append(role)

    if len(roles_to_add) > 0:
        await bot.add_roles(ctx.message.author, *roles_to_add)
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you now have every WUG member role.'.format(ctx), colour=discord.Colour.teal()))
    else:
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you already have every WUG member role.'.format(ctx), colour=discord.Colour.red()))

@bot.command(name='kamioshi-count', pass_context=True, no_pm=True)
async def kamioshi_count(ctx):
    await bot.send_typing(ctx.message.channel)
    ids_to_member = hkd.get_role_ids()
    oshi_num = {}
    for member in ctx.message.server.members:
        member_roles = [r for r in member.roles if r.id in ids_to_member]
        if len(member_roles) > 0:
            role = sorted(member_roles)[-1]
            oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1

    description = ''
    for oshi in sorted(oshi_num.items(), key=itemgetter(1), reverse=True):
        description += '**{0}** ({1.mention}) - {2}\n'.format(oshi[0].title(), get_wug_role(ctx.message.server, oshi[0]), oshi[1])
    await bot.say(content='**Number of Users with Each WUG Member Role as Their Highest Role**', embed=create_embed(description=description))

@bot.command(name='oshi-count', pass_context=True, no_pm=True)
async def oshi_count(ctx):
    await bot.send_typing(ctx.message.channel)
    ids_to_member = hkd.get_role_ids()
    oshi_num = {}
    for member in ctx.message.server.members:
        for role in member.roles:
            if role.id in ids_to_member:
                oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1

    description = ''
    for oshi in sorted(oshi_num.items(), key=itemgetter(1), reverse=True):
        description += '**{0}** ({1.mention}) - {2}\n'.format(oshi[0].title(), get_wug_role(ctx.message.server, oshi[0]), oshi[1])
    await bot.say(content='**Number of Users with Each WUG Member Role**', embed=create_embed(description=description))

@bot.command(pass_context=True, no_pm=True)
async def events(ctx, *, date : str=''):
    await bot.send_typing(ctx.message.channel)
    event_urls = []
    search_date = parser.parse(date) if date else datetime.now(pytz.timezone('Japan'))
    first = True
    for _ in range(3):
        with suppress(Exception):
            html_response = urlopen('https://www.eventernote.com/events/month/{0}-{1}-{2}/1?limit=1000'.format(search_date.year, search_date.month, search_date.day))
            soup = BeautifulSoup(html_response, 'html.parser')
            result = soup.find_all(attrs={'class': ['date', 'event', 'actor', 'note_count']})

            for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                info = event[1].find_all('a')
                event_time = event[1].find('span')
                event_url = info[0]['href']
                if event_url not in event_urls:
                    performers = [p.contents[0] for p in event[2].find_all('a')]
                    wug_performers = [p for p in performers if p in hkd.WUG_MEMBERS]
                    if not wug_performers:
                        continue
                    await bot.send_typing(ctx.message.channel)
                    colour = get_wug_role(ctx.message.server, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]).colour if len(wug_performers) == 1 else discord.Colour.teal()
                    if first:
                        first = False
                        await bot.say('**Events Involving WUG Members on {0:%Y}-{0:%m}-{0:%d} ({0:%A})**'.format(search_date))
                        await bot.send_typing(ctx.message.channel)
                        await asyncio.sleep(0.5)
                    other_performers = [p for p in performers if p not in hkd.WUG_MEMBERS and p != 'Wake Up, Girls!']
                    embed_fields = []
                    embed_fields.append(('Location', info[1].contents[0]))
                    embed_fields.append(('Time', event_time.contents[0] if event_time else 'To be announced'))
                    embed_fields.append(('WUG Members', ', '.join(wug_performers)))
                    embed_fields.append(('Other Performers', ', '.join(other_performers) if other_performers else 'None'))
                    embed_fields.append(('Eventernote Attendees', event[3].find('p').contents[0]))
                    event_urls.append(event_url)
                    await asyncio.sleep(0.5)
                    await bot.say(embed=create_embed(title=info[0].contents[0], colour=colour, url='https://www.eventernote.com{0}'.format(event_url), thumbnail=event[0].find('img')['src'], fields=embed_fields, inline=True))
            break

    if not event_urls:
        await bot.say(embed=create_embed(description='Couldn\'t find any events on that day.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def eventsin(ctx, month : str, member : str=''):
    await bot.send_typing(ctx.message.channel)
    search_month = hkd.parse_month(month)
    if search_month == 'None':
        await bot.say(embed=create_embed(description='Couldn\'t find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.', colour=discord.Colour.red()))
        return
    current_time = datetime.now(pytz.timezone('Japan'))
    search_year = str(current_time.year if current_time.month <= int(search_month) else current_time.year + 1)
    search_index = [0]
    wug_names = list(hkd.WUG_ROLE_IDS.keys())
    if member:
        if member.lower() not in wug_names:
            await bot.say(embed=create_embed(description='Couldn\'t find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.', colour=discord.Colour.red()))
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
                result = soup.find_all(attrs={'class': ['date', 'event', 'actor', 'note_count']})
                for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                    event_date = event[0].find('p').contents[0][:10]
                    if event_date[:4] == search_year and event_date[5:7] == search_month:
                        search_start = True
                    else:
                        if search_start:
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
                        await bot.send_typing(ctx.message.channel)
                        colour = get_wug_role(ctx.message.server, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]).colour if len(wug_performers) == 1 else discord.Colour.teal()
                        if first:
                            first = False
                            await bot.say('**Events for {0} in {1} {2}**'.format(member.title() if member else 'Wake Up, Girls!', month_name[int(search_month)], search_year))
                            await asyncio.sleep(0.5)
                        other_performers = [p for p in performers if p not in hkd.WUG_MEMBERS and p != 'Wake Up, Girls!']
                        embed_fields = []
                        embed_fields.append(('Location', info[1].contents[0]))
                        embed_fields.append(('Date', '{0} ({1:%A})'.format(event_date, parser.parse(event_date))))
                        embed_fields.append(('Time', event_time.contents[0] if event_time else 'To be announced'))
                        embed_fields.append(('WUG Members', ', '.join(wug_performers)))
                        embed_fields.append(('Other Performers', ', '.join(other_performers) if other_performers else 'None'))
                        embed_fields.append(('Eventernote Attendees', event[3].find('p').contents[0]))
                        event_urls.append(event_url)
                        await asyncio.sleep(0.5)
                        await bot.say(embed=create_embed(title=info[0].contents[0], colour=colour, url='https://www.eventernote.com{0}'.format(event_url), thumbnail=event[0].find('img')['src'], fields=embed_fields, inline=True))
                break

    if not event_urls:
        await bot.say(embed=create_embed(description='Couldn\'t find any events during that month.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def tagcreate(ctx, *, tag_to_create : str):
    await bot.send_typing(ctx.message.channel)
    split_request = tag_to_create.split()
    if len(split_request) > 1:
        tag_name = split_request[0]
        tag_content = tag_to_create[len(tag_name) + 1:]
        if tag_name not in firebase_ref.child('tags').get():
            firebase_ref.child('tags/{0}'.format(tag_name)).set(tag_content)
            await bot.say(embed=create_embed(title='Successfully created tag - {0}'.format(tag_name)))
        else:
            await bot.say(embed=create_embed(title='That tag already exists. Please choose a different tag name.', colour=discord.Colour.red()))
        return
    await bot.say(embed=create_embed(description='Couldn\'t create tag. Please follow this format for creating a tag: **!tagcreate** *NameOfTag* *Content of the tag*.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def tagupdate(ctx, *, tag_to_update : str):
    await bot.send_typing(ctx.message.channel)
    split_update = tag_to_update.split()
    if len(split_update) > 1:
        tag_name = split_update[0]
        updated_content = tag_to_update[len(tag_name) + 1:]
        if tag_name in firebase_ref.child('tags').get():
            firebase_ref.child('tags/{0}'.format(tag_name)).set(updated_content)
            await bot.say(embed=create_embed(title='Successfully updated tag - {0}.'.format(tag_name)))
        else:
            await bot.say(embed=create_embed(title='That tag doesn\'t exist.'.format(tag_name)))
        return
    await bot.say(embed=create_embed(description='Couldn\'t update tag. Please follow this format for updating a tag: **!tagupdate** *NameOfTag* *Updated content of the tag*.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def tagdelete(ctx, tag_name : str):
    await bot.send_typing(ctx.message.channel)
    if firebase_ref.child('tags/{0}'.format(tag_name)).get():
        firebase_ref.child('tags/{0}'.format(tag_name)).delete()
        await bot.say(embed=create_embed(title='Successfully removed tag - {0}.'.format(tag_name)))
    else:
        await bot.say(embed=create_embed(title='That tag doesn\'t exist.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def tagsearch(ctx):
    await bot.send_typing(ctx.message.channel)
    tag_list = firebase_ref.child('tags').get()
    await bot.say(content='Existing Tags', embed=create_embed(title=', '.join(list(tag_list.keys()))))

@bot.command(pass_context=True, no_pm=True)
async def tag(ctx, tag_name : str):
    await bot.send_typing(ctx.message.channel)
    tag_result = firebase_ref.child('tags/{0}'.format(tag_name)).get()
    if tag_result:
        split_tag = hkd.split_embeddable_content(tag_result)
        if not split_tag:
            await bot.say(tag_result)
        else:
            for link in split_tag:
                await bot.send_typing(ctx.message.channel)
                await asyncio.sleep(1)
                await bot.say(link)

            await asyncio.sleep(3)
            async for message in bot.logs_from(ctx.message.channel, after=ctx.message):
                if message.author == bot.user and not message.embeds:
                    if hkd.is_image_file(message.content) or hkd.is_video_link(message.content) or 'twitter.com' in message.content:
                        link_url = message.content
                        await bot.edit_message(message, 'Reposting link...')
                        await asyncio.sleep(1)
                        await bot.edit_message(message, link_url)
    else:
        await bot.say(embed=create_embed(description='That tag doesn\'t exist. Use **!tagcreate** *tag_name* *Content of the tag* to create a tag.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def pollcreate(ctx, duration : int, *, topic : str):
    await bot.send_typing(ctx.message.channel)
    if duration > 120:
        await bot.say(embed=create_embed(title='Please specify a duration of less than 2 hours.', colour=discord.Colour.red()))
        return
    elif duration < 1:
        await bot.say(embed=create_embed(title='Please specify a duration of at least 1 minute.', colour=discord.COlour.red()))
        return

    if not poll.topic:
        poll.create(topic, ctx.message.author.id, duration, ctx.message.channel.id)
        await bot.say(embed=create_embed(description='Poll successfully created. Please specify the options for the poll with **!polloptions** *options*, e.g. **!polloptions** first option, second option, third option.'))
    else:
        await bot.say(embed=create_embed(description='There is already an ongoing poll. Please wait for the current poll to end, or if you are the creator of the current poll, you can end it with **!pollend**.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def polloptions(ctx, *, options : str):
    await bot.send_typing(ctx.message.channel)
    if not poll.topic:
        await bot.say(embed=create_embed(description='There is no created poll to provide options for. You can create a poll with **!pollcreate** *duration* *topic*.', colour=discord.Colour.red()))
        return
    if ctx.message.author.id != poll.owner:
        await bot.say(embed=create_embed(title='Only the creator of the poll can specify the options.', colour=discord.Colour.red()))
        return
    if poll.options:
        await bot.say(embed=create_embed(description='The options for this poll have already been specified. Please wait for the current poll to end, or if you are the creator of the current poll, you can end it with **!pollend**.', colour=discord.Colour.red()))
        return

    poll_options = [p.strip() for p in options.split(',')]
    if len(poll_options) < 2:
        await bot.say(embed=create_embed(title='Please specify more than one option for the poll.', colour=discord.Colour.red()))
        return
    poll.set_options(poll_options, time.time() + poll.duration * 60)
    description = 'Vote for an option with **!vote** *number*, e.g. **!vote** 1 for option 1.\n\n'
    description += poll.get_details()
    await bot.say(content='Poll created. This poll will last for {0}. The creator of the poll may end it early with **!pollend**.'.format(format_timespan(poll.duration * 60)), embed=create_embed(title=poll.topic, description=description))

@bot.command(pass_context=True, no_pm=True)
async def polldetails(ctx):
    await bot.send_typing(ctx.message.channel)
    if not poll.options:
        await bot.say(embed=create_embed(description='There is no poll currently ongoing. You can create a poll with **!pollcreate** *duration* *topic*.', colour=discord.Colour.red()))
        return
    description = 'Vote for an option with **!vote** *number*, e.g. **!vote** 1 for option 1.\n\n'
    description += poll.get_details()
    await bot.say(content='Details of the currently running poll.', embed=create_embed(title=poll.topic, description=description))

@bot.command(pass_context=True, no_pm=True)
async def pollend(ctx):
    await bot.send_typing(ctx.message.channel)
    if not poll.topic:
        await bot.say(embed=create_embed(description='There is no poll currently ongoing. You can create a poll with **!pollcreate** *duration* *topic*.', colour=discord.Colour.red()))
        return
    if not poll.options:
        await bot.say(embed=create_embed(description='A poll was created but no options provided. The poll has been cancelled.'))
        return
    if ctx.message.author.id != poll.owner:
        await bot.say(embed=create_embed(title='Only the creator of the poll can end it.', colour=discord.Colour.red()))
        return
    topic = poll.topic
    await bot.say(content='Poll ended.', embed=create_embed(title=topic, description=poll.end()))

@bot.command(pass_context=True, no_pm=True)
async def vote(ctx, option : int):
    if not poll.options:
        await bot.say(embed=create_embed(title='There is no currently ongoing poll.', colour=discord.Colour.red()))
        return
    if option > len(poll.options):
        await bot.say(embed=create_embed(title='The currently running poll does not have that many options. Use **!polldetails** to see the options.', colour=discord.Colour.red()))
        return
    poll.vote(option, ctx.message.author.id)

@bot.command(pass_context=True, no_pm=True)
async def userinfo(ctx, member : discord.Member=None):
    await bot.send_typing(ctx.message.channel)
    user = member or ctx.message.author
    embed_fields = []
    embed_fields.append(('Name', '{0}'.format(user.display_name)))
    embed_fields.append(('ID', '{0}'.format(user.id)))
    embed_fields.append(('Joined Server', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(user.joined_at)))
    embed_fields.append(('Account Created', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(user.created_at)))
    embed_fields.append(('Roles', '{0}'.format(', '.join([r.name for r in user.roles[1:]]) if len(user.roles[1:]) > 0 else 'None')))
    embed_fields.append(('Avatar', '{0}'.format('<{0}>'.format(user.avatar_url) if user.avatar_url else 'None')))
    await bot.say(content='**User Information for {0.mention}**'.format(user), embed=create_embed(fields=embed_fields, inline=True))

@bot.command(pass_context=True, no_pm=True)
async def serverinfo(ctx):
    await bot.send_typing(ctx.message.channel)
    server = ctx.message.server
    embed_fields = []
    embed_fields.append(('{0}'.format(server.name), '(ID: {0})'.format(server.id)))
    embed_fields.append(('Owner', '{0} (ID: {1})'.format(server.owner, server.owner.id)))
    embed_fields.append(('Members', '{0}'.format(server.member_count)))
    embed_fields.append(('Channels', '{0} text, {1} voice'.format(sum(1 if str(channel.type) == 'text' else 0 for channel in server.channels), sum(1 if str(channel.type) == 'voice' else 0 for channel in server.channels))))
    embed_fields.append(('Roles', '{0}'.format(len(server.roles))))
    embed_fields.append(('Created On', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(server.created_at)))
    embed_fields.append(('Default Channel', '{0}'.format(server.default_channel.name if server.default_channel is not None else 'None')))
    embed_fields.append(('Region', '{0}'.format(server.region)))
    embed_fields.append(('Icon', '{0}'.format('<{0}>'.format(server.icon_url) if server.icon_url else 'None')))
    await bot.say(content='**Server Information**', embed=create_embed(fields=embed_fields, inline=True))

@bot.command(pass_context=True)
async def blogpics(ctx, member : str=''):
    await bot.send_typing(ctx.message.channel)
    for _ in range(3):
        with suppress(Exception):
            html_response = urlopen('https://ameblo.jp/wakeupgirls')
            soup = BeautifulSoup(html_response, 'html.parser')
            blog_title = soup.find('h2')
            member_sign = blog_title.find('a').contents[0]

            day = -1
            for i, sign in enumerate(hkd.WUG_BLOG_ORDER):
                if sign in member_sign:
                    day = i
                    if not member:
                        member = [m for m in hkd.WUG_BLOG_SIGNS.keys() if hkd.WUG_BLOG_SIGNS[m] == sign][0]
            if day == -1:
                await bot.say(embed=create_embed(description='Couldn\'t find pictures for that member.', colour=discord.Colour.red()))
                return

            page, entry_num = map(sum, zip(divmod((hkd.WUG_BLOG_ORDER.index(hkd.WUG_BLOG_SIGNS[member.lower()]) - day) % 7, 3), (1, 1)))

            if page != 1:
                html_response = urlopen('https://ameblo.jp/wakeupgirls/page-{0}.html'.format(page))
                soup = BeautifulSoup(html_response, 'html.parser')

            blog_entry = soup.find_all(attrs={'class': 'skin-entryBody'}, limit=entry_num)[entry_num - 1]
            pics = [p['href'] for p in blog_entry.find_all('a') if hkd.is_image_file(p['href'])]
            for pic in pics:
                await bot.send_typing(ctx.message.channel)
                await asyncio.sleep(1)
                await bot.say(pic)
            break

    if len(pics) == 0:
        await bot.say(embed=create_embed(description='Couldn\'t find any pictures.', colour=discord.Colour.red()))
        return

    await asyncio.sleep(3)
    async for message in bot.logs_from(ctx.message.channel, after=ctx.message):
        if message.author == bot.user and hkd.is_image_file(message.content) and not message.embeds:
            image_url = message.content
            await bot.edit_message(message, 'Reposting picture...')
            await asyncio.sleep(1)
            await bot.edit_message(message, image_url)

@bot.command(pass_context=True)
async def mv(ctx, *, song_name : str):
    await bot.send_typing(ctx.message.channel)
    name_to_mv = {}
    for mv, names in list(firebase_ref.child('music_videos/mv_aliases').get().items()):
        name_to_mv.update({name : mv for name in names})

    song = hkd.parse_mv_name(song_name)
    if song in name_to_mv:
        await bot.say(firebase_ref.child('music_videos/mv_links').get()[name_to_mv[song]])
    else:
        await bot.say(embed=create_embed(description='Couldn\'t find that MV. Use **!mv-list** to show the list of available MVs.', colour=discord.Colour.red()))

@bot.command(name='mv-list', pass_context=True)
async def mv_list(ctx):
    await bot.send_typing(ctx.message.channel)
    description = '{0}\n\n'.format('\n'.join(list(firebase_ref.child('music_videos/mv_links').get().keys())))
    description += 'Use **!mv** *song* to show the full MV. You can also write the name of the song in English.'
    await bot.say(content='**List of Available Music Videos**', embed=create_embed(description=description))

@bot.command(name='seiyuu-vids', pass_context=True)
async def seiyuu_vids(ctx):
    await bot.send_typing(ctx.message.channel)
    await bot.say(content='**WUG Seiyuu Videos**', embed=create_embed(title='List of seiyuu content on the Wake Up, Girls! wiki', url='http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content'))

@bot.command(name='wugch-omake', pass_context=True, no_pm=True)
async def wugch_omake(ctx):
    await bot.send_typing(ctx.message.channel)
    await bot.say(content='**WUG Channel Omake Videos**', embed=create_embed(title='Google Drive folder with recent WUGch omake videos', url='https://drive.google.com/open?id=1o0PWGdlCUhsIN72O0aKSP6HRbim5Fzpw'))

@bot.command(pass_context=True)
async def tl(ctx, *, text : str):
    await bot.send_typing(ctx.message.channel)
    await bot.say(embed=create_embed(description=Translator().translate(text, src='ja', dest='en').text))

@bot.command(pass_context=True)
async def currency(ctx, *conversion : str):
    await bot.send_typing(ctx.message.channel)
    if len(conversion) == 4 and conversion[2].lower() == 'to':
        with suppress(Exception):
            result = CurrencyRates().convert(conversion[1].upper(), conversion[3].upper(), Decimal(conversion[0]))
            await bot.say(embed=create_embed(title='{0} {1}'.format(('{:f}'.format(result)).rstrip('0').rstrip('.'), conversion[3].upper())))
            return
    await bot.say(embed=create_embed(description='Couldn\'t convert. Please follow this format for converting currency: **!currency** 12.34 AUD to USD.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def weather(ctx, *, location : str):
    await bot.send_typing(ctx.message.channel)
    query = location.split(',')
    if len(query) > 1:
        with suppress(Exception):
            query[1] = pycountry.countries.get(name=query[1].strip().title()).alpha_2
    with suppress(Exception):
        result = requests.get('http://api.openweathermap.org/data/2.5/weather', params={'q': ','.join(query), 'APPID': config['weather_api_key']}).json()
        timezone = pytz.timezone(TimezoneFinder().timezone_at(lat=result['coord']['lat'], lng=result['coord']['lon']))
        embed_fields = []
        embed_fields.append(('Weather', '{0}'.format(result['weather'][0]['description'].title())))
        embed_fields.append(('Temperature', '{0} °C, {1} °F'.format('{0:.2f}'.format(float(result['main']['temp']) - 273.15), '{0:.2f}'.format(1.8 * (float(result['main']['temp']) - 273.15) + 32.0))))
        embed_fields.append(('Humidity', '{0}%'.format(result['main']['humidity'])))
        embed_fields.append(('Wind Speed', '{0} m/s'.format(result['wind']['speed'])))
        embed_fields.append(('Sunrise', '{0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunrise'], tz=timezone))))
        embed_fields.append(('Sunset', '{0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunset'], tz=timezone))))
        embed_fields.append(('Pressure', '{0} hPa'.format(result['main']['pressure'])))
        await bot.say(content='**Weather for {0}, {1}**'.format(result['name'], pycountry.countries.lookup(result['sys']['country']).name), embed=create_embed(fields=embed_fields, inline=True))
        return
    await bot.say(embed=create_embed(description='Couldn\'t get weather. Please follow this format for checking the weather: **!weather** Melbourne, Australia.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def choose(ctx, *options : str):
    await bot.send_typing(ctx.message.channel)
    if len(options) > 1:
        await bot.say(embed=create_embed(description=options[randrange(len(options))]))
    else:
        await bot.say(embed=create_embed(description='Please provide 2 or more options to choose from, e.g. **!choose** *option1* *option2*.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def yt(ctx, *, query : str):
    await bot.send_typing(ctx.message.channel)
    for _ in range(3):
        with suppress(Exception):
            html_response = urlopen('https://www.youtube.com/results?search_query={0}'.format(quote(query)))
            soup = BeautifulSoup(html_response, 'html.parser')
            for result in soup.find_all(attrs={'class': 'yt-uix-tile-link'}):
                link = result['href']
                if hkd.is_youtube_link(link):
                    await bot.say('https://www.youtube.com{0}'.format(link))
                    return
            break
    await bot.say(embed=create_embed(title='Couldn\'t find any results.', colour=discord.Colour.red()))

@bot.command(name='dl-vid', pass_context=True, no_pm=True)
async def dl_vid(ctx, url : str):
    await bot.send_typing(ctx.message.channel)
    await bot.say('Attempting to download the video using youtube-dl. Please wait.')
    niconico_vid = 'nicovideo.jp' in url
    proc = subprocess.run(args=['youtube-dl', '--get-filename', url], universal_newlines=True, stdout=subprocess.PIPE)
    vid_filename = proc.stdout.strip()

    if niconico_vid and not vid_filename:
        url = url.rstrip('/')
        niconico_id = url[url.rfind('/') + 1:]
        vid_filename = 'nicovideo_{0}.mp4'.format(niconico_id)

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
                await bot.say(embed=create_embed(title='Failed to download video.', colour=discord.Colour.red()))
                with suppress(Exception):
                    os.remove('{0}.part'.format(vid_filename))
                return
        retry = False

    await bot.say('Download complete. Now uploading video to Google Drive. Please wait.')

    proc = subprocess.Popen(args=['python', 'gdrive_upload.py', vid_filename, config['uploads_folder']])
    while proc.poll() is None:
        await asyncio.sleep(1)

    if proc.returncode != 0:
        await bot.say(embed=create_embed(title='Failed to upload video to Google Drive.', colour=discord.Colour.red()))
        with suppress(Exception):
            os.remove(vid_filename)
        return

    await bot.say(content='{0.mention}'.format(ctx.message.author), embed=create_embed(description='Upload complete. Your video is available here: https://drive.google.com/open?id={0}. The Google Drive folder has limited space so it will be purged from time to time.'.format(config['uploads_folder'])))

@bot.command(pass_context=True)
async def say(ctx, channel_name : str, *, message : str):
    if ctx.message.author.id != hkd.BOT_ADMIN_ID:
        return

    server = discord.utils.get(bot.servers, id=hkd.SERVER_ID)
    channel = discord.utils.get(server.channels, name=channel_name)
    await bot.send_typing(channel)
    await asyncio.sleep(1.5)
    await bot.send_message(channel, message)

bot.loop.create_task(check_mute_status())
bot.loop.create_task(check_tweets())
bot.loop.create_task(check_poll_status())
bot.loop.create_task(check_wugch_omake())
bot.loop.create_task(check_live_streams())
bot.run(config['token'])