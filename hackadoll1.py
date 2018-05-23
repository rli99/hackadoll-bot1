import asyncio, discord, pycountry, pytz, requests, time, twitter
import hkdhelper as hkd
from bs4 import BeautifulSoup
from calendar import month_name
from datetime import datetime
from dateutil import parser
from decimal import Decimal
from discord.ext import commands
from firebase_admin import credentials, db, initialize_app
from forex_python.converter import CurrencyRates
from googletrans import Translator
from hkdhelper import create_embed, get_muted_role, get_wug_role 
from humanfriendly import format_timespan
from math import ceil
from operator import itemgetter
from random import randrange
from timezonefinder import TimezoneFinder
from urllib.parse import quote
from urllib.request import urlopen

config = hkd.parse_config()
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
certificate = credentials.Certificate(config['firebase_credentials'])
firebase = initialize_app(certificate, {'databaseURL': config['firebase_db']})
firebase_ref = db.reference()
muted_members = firebase_ref.child('muted_members').get() or {}
twitter_api = twitter.Api(consumer_key=config['consumer_key'], consumer_secret=config['consumer_secret'], access_token_key=config['access_token_key'], access_token_secret=config['access_token_secret'])

@bot.event
async def on_ready():
    print('\n-------------\nLogged in as: {0} ({1})\n-------------\n'.format(bot.user.name, bot.user.id))

@bot.event
async def check_mute_status():
    await bot.wait_until_ready()
    while not bot.is_closed:
        members_to_unmute = []
        for member_id in muted_members:
            if time.time() > int(muted_members[member_id]):
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
        for name in hkd.WUG_TWITTER_NAMES:
            last_tweet_id = int(firebase_ref.child('last_tweet_ids/{0}'.format(name)).get())
            posted_tweets = []
            for status in twitter_api.GetUserTimeline(screen_name=name, since_id=last_tweet_id, count=40, include_rts=False):
                tweet = status.AsDict()
                tweet_id = tweet['id']
                if tweet_id > last_tweet_id:
                    await bot.send_typing(channel)
                    posted_tweets.append(tweet_id)
                    await asyncio.sleep(1)
                    await bot.send_message(channel, 'https://twitter.com/{0}/status/{1}'.format(name, tweet_id))
            if posted_tweets:
                firebase_ref.child('last_tweet_ids/{0}'.format(name)).set(str(max(posted_tweets)))
        await asyncio.sleep(20)

@bot.command(pass_context=True)
async def help(ctx):
    await bot.send_typing(ctx.message.channel)
    embed_fields = []
    embed_fields.append(('!help', 'Show this help message.'))
    embed_fields.append(('!kick *member*', 'Kick a member (mods only).'))
    embed_fields.append(('!ban *member*', 'Ban a member (mods only).'))
    embed_fields.append(('!mute *member* *duration*', 'Mute a member for *duration* minutes (mods only).'))
    embed_fields.append(('!unmute *member*', 'Unmute a member (mods only).'))
    embed_fields.append(('!userinfo', 'Show your user information.'))
    embed_fields.append(('!serverinfo', 'Show server information.'))
    embed_fields.append(('!oshihen *member*', 'Change your oshi role.'))
    embed_fields.append(('!oshimashi *member*', 'Get an additional oshi role.'))
    embed_fields.append(('!hakooshi', 'Get all 7 WUG member roles.'))
    embed_fields.append(('!roles', 'Show additional help on how to get roles.'))
    embed_fields.append(('!kamioshi-count', 'Show the number of members with each WUG member role as their highest role.'))
    embed_fields.append(('!oshi-count', 'Show the number of members with each WUG member role.'))
    embed_fields.append(('!blogpics *member*', 'Get pictures from the latest blog post of the specified WUG member (optional). If *member* not specified, gets pictures from the latest blog post.'))
    embed_fields.append(('!events *date*', 'Get information for events involving WUG members on the specified date. If *date* not specified, finds events happening today.'))
    embed_fields.append(('!eventsin *month* *member*', 'Get information for events involving WUG members for the specified month and member, e.g. **!eventsin** April Mayushii. Searches events from this month onwards only.'))
    embed_fields.append(('!mv *song*', 'Show full MV of a song.'))
    embed_fields.append(('!mv-list', 'Show list of available MVs.'))
    embed_fields.append(('!seiyuu-vids', 'Show link to the wiki page with WUG seiyuu content.'))
    embed_fields.append(('!tl *japanese text*', 'Translate the provided Japanese text into English via Google Translate.'))
    embed_fields.append(('!currency *amount* *x* to *y*', 'Convert *amount* of *x* currency to *y* currency, e.g. **!currency** 12.34 AUD to USD'))
    embed_fields.append(('!weather *city*, *country*', 'Show weather information for *city*, *country* (optional), e.g. **!weather** Melbourne, Australia'))
    embed_fields.append(('!tagcreate *tag_name* *content*', 'Create a tag.'))
    embed_fields.append(('!tag *tag_name*', 'Display a saved tag.'))
    embed_fields.append(('!choose *options*', 'Randomly choose from one of the provided options, e.g. **!choose** option1 option2'))
    embed_fields.append(('!yt *query*', 'Gets the top result from YouTube based on the provided search terms.'))
    await bot.say(content='**Available Commands**', embed=create_embed(fields=embed_fields))

@bot.command(pass_context=True, no_pm=True)
async def kick(ctx, member : discord.Member):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.kick_members:
        try:
            await bot.say(embed=create_embed(title='{0} has been kicked.'.format(member)))  
            await bot.kick(member)
            return
        except: pass
    await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def ban(ctx, member : discord.Member):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.ban_members:
        try:
            await bot.say(embed=create_embed(title='{0} has been banned.'.format(member)))
            await bot.ban(member)
            return
        except: pass
    await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def mute(ctx, member : discord.Member, duration : int):
    await bot.send_typing(ctx.message.channel)
    if ctx.message.author.server_permissions.kick_members:
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

@bot.command(pass_context=True, no_pm=True)
async def roles(ctx):
    await bot.send_typing(ctx.message.channel)
    description = 'Users can have any of the 7 WUG member roles. Use **!oshihen** *member* to get the role you want.\n\n'
    for oshi in hkd.WUG_ROLE_IDS.keys():
        description += '**!oshihen** {0} for {1.mention}\n'.format(oshi.title(), get_wug_role(ctx.message.server, oshi))
    description += '\nNote that using **!oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **!oshimashi** *member* instead. To get all 7 roles, use **!hakooshi**.'
    await bot.say(content='**How to get WUG Member Roles**', embed=create_embed(description=description))

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

@bot.command(pass_context=True)
async def blogpics(ctx, member : str=''):
    await bot.send_typing(ctx.message.channel)
    page = 1
    entry_num = 1
    day = -1
    try:
        html_response = urlopen('https://ameblo.jp/wakeupgirls')
        soup = BeautifulSoup(html_response, 'html.parser')
        blog_entry = soup.find(attrs={'class': 'skin-entryBody'})
        sign_entry = hkd.strip_from_end(str(blog_entry)[:-10].strip(), '<br/>')
        member_sign = sign_entry[sign_entry.rfind('>') + 3:]

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

        if page != 1 or entry_num != 1:
            blog_entry = soup.find_all(attrs={'class': 'skin-entryBody'}, limit=entry_num)[entry_num - 1]

        for pic in [p['href'] for p in blog_entry.find_all('a') if p['href'][-4:] == '.jpg']:
            await bot.send_typing(ctx.message.channel)
            await asyncio.sleep(2)
            await bot.say(pic)
        return
    except:
        await bot.say(embed=create_embed(description='Couldn\'t get pictures right now. Try again a bit later.', colour=discord.Colour.red()))

@bot.command(pass_context=True, no_pm=True)
async def events(ctx, *, date : str=''):
    await bot.send_typing(ctx.message.channel)
    event_urls = []
    search_date = parser.parse(date) if date else datetime.now(pytz.timezone('Japan'))
    first = True

    for member in hkd.WUG_MEMBERS:
        html_response = urlopen('https://www.eventernote.com/events/search?keyword={0}&year={1}&month={2}&day={3}'.format(quote(member), search_date.year, search_date.month, search_date.day))
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
                colour = get_wug_role(ctx.message.server, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]).colour if len(wug_performers) == 1 else discord.Colour.default()
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

    first = True
    search_start = False
    event_urls = []
    for i in search_index:
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
                colour = get_wug_role(ctx.message.server, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]).colour if len(wug_performers) == 1 else discord.Colour.default()
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

    if not event_urls:
        await bot.say(embed=create_embed(description='Couldn\'t find any events during that month.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def mv(ctx, *, song_name : str):
    await bot.send_typing(ctx.message.channel)
    name_to_mv = {}
    for mv, names in list(hkd.MV_NAMES.items()):
      name_to_mv.update({name : mv for name in names})

    song = hkd.parse_mv_name(song_name)
    if song in name_to_mv:
        await bot.say(hkd.MUSICVIDEOS[name_to_mv[song]])
    else:
        await bot.say(embed=create_embed(description='Couldn\'t find that MV. Use **!mv-list** to show the list of available MVs.', colour=discord.Colour.red()))

@bot.command(name='mv-list', pass_context=True)
async def mv_list(ctx):
    await bot.send_typing(ctx.message.channel)
    description = '{0}\n\n'.format('\n'.join(list(hkd.MUSICVIDEOS.keys())))
    description += 'Use **!mv** *song* to show the full MV. You can also write the name of the song in English.'
    await bot.say(content='**List of Available Music Videos**', embed=create_embed(description=description))

@bot.command(name='seiyuu-vids', pass_context=True)
async def seiyuu_vids(ctx):
    await bot.send_typing(ctx.message.channel)
    await bot.say(content='**WUG Seiyuu Videos**', embed=create_embed(title='Wake Up, Girls! Wiki - List of Seiyuu Content', url='http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content'))

@bot.command(pass_context=True)
async def tl(ctx, *, text : str):
    await bot.send_typing(ctx.message.channel)
    await bot.say(embed=create_embed(description=Translator().translate(text, src='ja', dest='en').text))

@bot.command(pass_context=True)
async def currency(ctx, *conversion : str):
    await bot.send_typing(ctx.message.channel)
    if len(conversion) == 4 and conversion[2].lower() == 'to':
        try:
            result = CurrencyRates().convert(conversion[1].upper(), conversion[3].upper(), Decimal(conversion[0]))
            await bot.say(embed=create_embed(title='{0} {1}'.format(('{:f}'.format(result)).rstrip('0').rstrip('.'), conversion[3].upper())))
            return
        except: pass
    await bot.say(embed=create_embed(description='Couldn\'t convert. Please follow this format for converting currency: **!currency** 12.34 AUD to USD.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def weather(ctx, *, location : str):
    await bot.send_typing(ctx.message.channel)
    query = location.split(',')
    if len(query) > 1:
        try:
            query[1] = pycountry.countries.get(name=query[1].strip().title()).alpha_2
        except: pass
    try:
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
    except: pass
    await bot.say(embed=create_embed(description='Couldn\'t get weather. Please follow this format for checking the weather: **!weather** Melbourne, Australia.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def tagcreate(ctx, *, tag_to_create : str):
    await bot.send_typing(ctx.message.channel)
    split_request = tag_to_create.split()
    if len(split_request) > 1:
        tag_name = split_request[0]
        tag_content = tag_to_create[len(tag_name) + 1:]
        existing_tag = firebase_ref.child('tags/{0}'.format(tag_name)).get()
        if not existing_tag:
            firebase_ref.child('tags/{0}'.format(tag_name)).set(tag_content)
            await bot.say(content='Created Tag.', embed=create_embed(title=tag_name))
            await bot.say(tag_content)
        else:
            await bot.say(embed=create_embed(title='That tag already exists. Please choose a different tag name.', colour=discord.Colour.red()))
        return
    await bot.say(embed=create_embed(description='Couldn\'t create tag. Please follow this format for creating a tag: **!tagcreate** *NameOfTag* *Content of the tag*.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def tag(ctx, tag_name : str):
    await bot.send_typing(ctx.message.channel)
    tag_result = firebase_ref.child('tags/{0}'.format(tag_name)).get()
    if tag_result and len(tag_result) > 0:
        await bot.say(tag_result)
    else:
        await bot.say(embed=create_embed(description='That tag doesn\'t exist. Use **!tagcreate** to create a tag.', colour=discord.Colour.red()))

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
    html_response = urlopen('https://www.youtube.com/results?search_query={0}'.format(quote(query)))
    soup = BeautifulSoup(html_response, 'html.parser')
    for result in soup.find_all(attrs={'class': 'yt-uix-tile-link'}):
        link = result['href']
        if link.find('googleads.g.doubleclick.net') == -1 and not link.startswith('/channel'):
            await bot.say('https://www.youtube.com{0}'.format(link))
            return
    await bot.say(embed=create_embed(title='Couldn\'t find any results.', colour=discord.Colour.red()))

bot.loop.create_task(check_mute_status())
bot.loop.create_task(check_tweets())
bot.run(config['token'])