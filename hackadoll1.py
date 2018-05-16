import asyncio, discord, pycountry, pytz, requests, time
from argparse import ArgumentParser
from datetime import datetime
from decimal import Decimal
from discord.ext import commands
from firebase import firebase
from forex_python.converter import CurrencyRates
from humanfriendly import format_timespan
from random import randrange
from timezonefinder import TimezoneFinder

def parse_arguments():
    parser = ArgumentParser(description='Discord bot for Wake Up, Girls! server.')
    parser.add_argument('--token', required=True, help='Token for the discord app bot user.')
    parser.add_argument('--firebase_db', required=True, metavar='DB_URL', help='URL for the Firebase Realtime Database.')
    parser.add_argument('--weather_api_key', required=True, metavar='KEY', help='API key for the OpenWeatherMap API.')
    return parser.parse_args()

WUG_ROLE_IDS = {'mayushii': '332788311280189443', 'aichan': '333727530680844288', 'minyami': '332793887200641028', 'yoppi': '332796755399933953', 'nanamin': '333721984196411392', 'kayatan': '333721510164430848', 'myu': '333722098377818115'}
MUSICVIDEOS = {'7 Girls War': 'https://streamable.com/1afp5', '言の葉 青葉': 'https://streamable.com/bn9mt', 'タチアガレ!': 'https://streamable.com/w85fh', '少女交響曲': 'https://streamable.com/gidqx', 'Beyond the Bottom': 'https://streamable.com/2ppw5', '僕らのフロンティア': 'https://streamable.com/pqydk', '恋?で愛?で暴君です!': 'https://streamable.com/88xas', 'One In A Billion': 'https://streamable.com/fa630', 'One In A Billion (Dance)': 'https://streamable.com/xbeeq', 'TUNAGO': 'https://streamable.com/4qjlp', '7 Senses': 'https://streamable.com/a34w9', '雫の冠': 'https://streamable.com/c6vfm', 'スキノスキル': 'https://streamable.com/w92kw'}
MV_NAMES = {'7 Girls War': ['7 girls war', '7gw'], '言の葉 青葉': ['言の葉 青葉', 'kotonoha aoba'], 'タチアガレ!': ['tachiagare!', 'タチアガレ!', 'tachiagare', 'タチアガレ'],  '少女交響曲': ['少女交響曲', 'skkk', 'shoujokkk', 'shoujo koukyoukyoku'], 'Beyond the Bottom': ['beyond the bottom', 'btb'], '僕らのフロンティア': ['僕らのフロンティア', 'bokufuro', '僕フロ', 'bokura no frontier'], '恋?で愛?で暴君です!': ['恋?で愛?で暴君です!', 'koiai', 'koi? de ai? de boukun desu!', 'koi de ai de boukun desu', 'boukun', 'ででです'], 'One In A Billion': ['one in a billion', 'oiab', 'ワンビリ'], 'One In A Billion (Dance)': ['one in a billion (dance)', 'oiab (dance)', 'ワンビリ (dance)', 'oiab dance'], 'TUNAGO': ['tunago'], '7 Senses': ['7 senses'], '雫の冠': ['雫の冠', 'shizuku no kanmuri'], 'スキノスキル': ['スキノスキル', 'suki no skill', 'sukinoskill']}
MUTED_ROLE_ID = '445572638543446016'
SERVER_ID = '280439975911096320'

args = parse_arguments()
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
firebase = firebase.FirebaseApplication(args.firebase_db, None)
muted_members = firebase.get('/muted_members', None) or {}

@bot.event
async def on_ready():
    print('\n-------------\nLogged in as: {0} ({1})\n-------------\n'.format(bot.user.name, bot.user.id))

@bot.event
async def check_mute_status():
    await bot.wait_until_ready()
    while not bot.is_closed:
        members_to_unmute = []
        for member_id in muted_members:
            if time.time() > muted_members[member_id]:
                firebase.delete('/muted_members', member_id)
                members_to_unmute.append(member_id)
                server = discord.utils.get(bot.servers, id=SERVER_ID)
                muted_role = discord.utils.get(server.roles, id=MUTED_ROLE_ID)
                member = discord.utils.get(server.members, id=member_id)
                await bot.remove_roles(member, muted_role)
        for member_id in members_to_unmute:
            muted_members.pop(member_id)
        await asyncio.sleep(30)

@bot.command()
async def help():
    embed_fields = []
    embed_fields.append(('!help', 'Show this help message.'))
    embed_fields.append(('!kick *member*', 'Kick a member (mods only).'))
    embed_fields.append(('!ban *member*', 'Ban a member (mods only).'))
    embed_fields.append(('!mute *member* *duration*', 'Mute a member for *duration* minutes (mods only).'))
    embed_fields.append(('!unmute *member*', 'Unmute a member (mods only).'))
    embed_fields.append(('!userinfo', 'Show your user information.'))
    embed_fields.append(('!serverinfo', 'Show server information.'))
    embed_fields.append(('!seiyuu-vids', 'Show link to the wiki page with WUG seiyuu content.'))
    embed_fields.append(('!oshihen *member*', 'Change your oshi role.'))
    embed_fields.append(('!oshimashi *member*', 'Get an additional oshi role.'))
    embed_fields.append(('!hakooshi', 'Get all 7 WUG member roles.'))
    embed_fields.append(('!roles', 'Show additional help on how to get roles.'))
    embed_fields.append(('!kamioshi-count', 'Show the number of members with each WUG member role as their highest role.'))
    embed_fields.append(('!oshi-count', 'Show the number of members with each WUG member role.'))
    embed_fields.append(('!mv *song*', 'Show full MV of a song.'))
    embed_fields.append(('!mv-list', 'Show list of available MVs.'))
    embed_fields.append(('!currency *amount* *x* to *y*', 'Convert *amount* of *x* currency to *y* currency, e.g. **!currency** 12.34 AUD to USD'))
    embed_fields.append(('!weather *city*, *country*', 'Show weather information for *city*, *country* (optional), e.g. **!weather** Melbourne, Australia'))
    embed_fields.append(('!tagcreate *tag_name* *content*', 'Create a tag.'))
    embed_fields.append(('!tag *tag_name*', 'Display a saved tag.'))
    embed_fields.append(('!choose *options*', 'Randomly choose from one of the provided options, e.g. **!choose** option1 option2'))
    await bot.say(content='**Available Commands**', embed=create_embed(fields=embed_fields))

@bot.command(pass_context=True)
async def kick(ctx, member : discord.Member):
    if ctx.message.channel.permissions_for(ctx.message.author).kick_members:
        try:
            await bot.say(embed=create_embed(title='{0.username}#{0.discriminator} has been kicked.'.format(member)))
            await bot.kick(member)  
            return
        except: pass
    await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def ban(ctx, member : discord.Member):
    if ctx.message.channel.permissions_for(ctx.message.author).ban_members:
        try:
            await bot.say(embed=create_embed(title='{0.username}#{0.discriminator} has been banned.'.format(member)))
            await bot.ban(member)
            return
        except: pass
    await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def mute(ctx, member : discord.Member, duration : int):
    if ctx.message.channel.permissions_for(ctx.message.author).ban_members:
        if duration > 0:
            mute_endtime = time.time() + duration * 60
            firebase.patch('/muted_members', {member.id : mute_endtime})
            muted_members[member.id] = mute_endtime
            muted_role = discord.utils.get(ctx.message.server.roles, id=MUTED_ROLE_ID)
            await bot.add_roles(member, muted_role)
            await bot.say(embed=create_embed(description='{0.mention} has been muted for {1}.'.format(member, format_timespan(duration * 60))))
        else:
            await bot.say(embed=create_embed(title='Please specify a duration greater than 0.', colour=discord.Colour.red()))
    else:
        await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def unmute(ctx, member : discord.Member):
    if ctx.message.channel.permissions_for(ctx.message.author).ban_members:
        firebase.delete('/muted_members', member.id)
        muted_members.pop(member.id)
        muted_role = discord.utils.get(ctx.message.server.roles, id=MUTED_ROLE_ID)
        await bot.remove_roles(member, muted_role)
        await bot.say(embed=create_embed(description='{0.mention} has been unmuted.'.format(member)))
    else:
        await bot.say(embed=create_embed(title='You do not have permission to do that.', colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def userinfo(ctx):
    user = ctx.message.author
    embed_fields = []
    embed_fields.append(('Name', '{0}\n'.format(user.display_name)))
    embed_fields.append(('ID', '{0}\n'.format(user.id)))
    embed_fields.append(('Joined server', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC\n'.format(user.joined_at)))
    embed_fields.append(('Account created', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC\n'.format(user.created_at)))
    embed_fields.append(('Roles', '{0}\n'.format(', '.join([r.name for r in user.roles[1:]]))))
    embed_fields.append(('Avatar', '<{0}>'.format(user.avatar_url)))
    await bot.say(content='**User Information for {0.mention}**'.format(user), embed=create_embed(fields=embed_fields, inline=True))

@bot.command(pass_context=True)
async def serverinfo(ctx):
    server = ctx.message.server
    embed_fields = []
    embed_fields.append(('{0}', '(ID: {1})\n'.format(server.name, server.id)))
    embed_fields.append(('Owner', '{0} (ID: {1})\n'.format(server.owner, server.owner.id)))
    embed_fields.append(('Members', '{0}\n'.format(server.member_count)))
    embed_fields.append(('Channels', '{0} text, {1} voice\n'.format(sum(1 if str(channel.type) == 'text' else 0 for channel in server.channels), sum(1 if str(channel.type) == 'voice' else 0 for channel in server.channels))))
    embed_fields.append(('Roles', '{0}\n'.format(len(server.roles))))
    embed_fields.append(('Created on', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC\n'.format(server.created_at)))
    embed_fields.append(('Default channel', '{0}\n'.format(server.default_channel.name if server.default_channel is not None else '')))
    embed_fields.append(('Region', '{0}\n'.format(server.region)))
    embed_fields.append(('Icon', '<{0}>'.format(server.icon_url)))
    await bot.say(content='**Server Information**', embed=create_embed(fields=embed_fields, inline=True))

@bot.command(name='seiyuu-vids')
async def seiyuu_vids():
    await bot.say(content='**WUG Seiyuu Videos**', embed=create_embed(title='Wake Up, Girls! Wiki - List of Seiyuu Content', url='http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content'))

@bot.command(pass_context=True)
async def oshihen(ctx, role_name : str):
    role = discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS[role_name.lower()])
    if role is None: 
        await bot.say(embed=create_embed(description='Couldn\'t find that role. Use **!roles** to show additional help on how to get roles.', colour=discord.Colour.red()))
        return

    roles_to_remove = []
    for existing_role in ctx.message.author.roles:
        if existing_role.id in WUG_ROLE_IDS.values():
            roles_to_remove.append(existing_role)

    if len(roles_to_remove) == 1 and roles_to_remove[0].name == role.name:
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=discord.Colour.red()))
    elif len(roles_to_remove) > 0:
        await bot.remove_roles(ctx.message.author, *roles_to_remove)
        await asyncio.sleep(1)
        
    await bot.add_roles(ctx.message.author, role)
    await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you have oshihened to the **{1}** role {2.mention}.'.format(ctx, role_name.title(), role), colour=role.colour))

@bot.command(pass_context=True)
async def oshimashi(ctx, role_name : str):
    role = discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS[role_name.lower()])
    if role is None:
        await bot.say(embed=create_embed(description='Couldn\'t find that role. Use **!roles** to show additional help on how to get roles.', colour=discord.Colour.red()))
        return

    if role not in ctx.message.author.roles:
        await bot.add_roles(ctx.message.author, role)
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you now have the **{1}** oshi role {2.mention}.'.format(ctx, role_name.title(), role), colour=role.colour))
    else:
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def hakooshi(ctx):
    roles_to_add = []
    for role in ctx.message.server.roles:
        if role not in ctx.message.author.roles and role.id in WUG_ROLE_IDS.values():
            roles_to_add.append(role)

    if len(roles_to_add) > 0:
        await bot.add_roles(ctx.message.author, *roles_to_add)
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you now have every WUG member role.'.format(ctx), colour=discord.Colour.teal()))
    else:
        await bot.say(embed=create_embed(description='Hello {0.message.author.mention}, you already have every WUG member role.'.format(ctx), colour=discord.Colour.red()))

@bot.command(pass_context=True)
async def roles(ctx):
    description = 'Users can have any of the 7 WUG member roles. Use **!oshihen** *member* to get the role you want.\n\n'
    description += '**!oshihen** Mayushii for {0.mention}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['mayushii']))
    description += '**!oshihen** Aichan for {0.mention}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['aichan']))
    description += '**!oshihen** Minyami for {0.mention}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['minyami']))
    description += '**!oshihen** Yoppi for {0.mention}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['yoppi']))
    description += '**!oshihen** Nanamin for {0.mention}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['nanamin']))
    description += '**!oshihen** Kayatan for {0.mention}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['kayatan']))
    description += '**!oshihen** Myu for {0.mention}\n\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['myu']))
    description += 'Note that using **!oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **!oshimashi** *member* instead. To get all 7 roles, use **!hakooshi**.'
    await bot.say(content='**How to get WUG Member Roles**', embed=create_embed(description=description))

@bot.command(name='kamioshi-count', pass_context=True)
async def kamioshi_count(ctx):
    ids_to_member = {v: k for k, v in WUG_ROLE_IDS.items()}
    oshi_num = {}
    for member in ctx.message.server.members:
        member_roles = [r for r in member.roles if r.id in ids_to_member]
        if len(member_roles) > 0:
            role = sorted(member_roles)[-1]
            if role.id in ids_to_member:
                oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1
 
    description = '**Mayushii** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['mayushii']), oshi_num.get('mayushii', 0))
    description += '**Aichan** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['aichan']), oshi_num.get('aichan', 0))
    description += '**Minyami** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['minyami']), oshi_num.get('minyami', 0))
    description += '**Yoppi** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['yoppi']), oshi_num.get('yoppi', 0))
    description += '**Nanamin** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['nanamin']), oshi_num.get('nanamin', 0))
    description += '**Kayatan** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['kayatan']), oshi_num.get('kayatan', 0))
    description += '**Myu** ({0.mention}) - {1}'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['myu']), oshi_num.get('myu', 0))
    await bot.say(content='**Number of Users with Each WUG Member Role as Their Highest Role**', embed=create_embed(description=description))

@bot.command(name='oshi-count', pass_context=True)
async def oshi_count(ctx):
    ids_to_member = {v: k for k, v in WUG_ROLE_IDS.items()}
    oshi_num = {}
    for member in ctx.message.server.members:
        for role in member.roles:
            if role.id in ids_to_member:
                oshi_num[ids_to_member[role.id]] = oshi_num.get(ids_to_member[role.id], 0) + 1

    description = '**Mayushii** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['mayushii']), oshi_num.get('mayushii', 0))
    description += '**Aichan** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['aichan']), oshi_num.get('aichan', 0))
    description += '**Minyami** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['minyami']), oshi_num.get('minyami', 0))
    description += '**Yoppi** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['yoppi']), oshi_num.get('yoppi', 0))
    description += '**Nanamin** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['nanamin']), oshi_num.get('nanamin', 0))
    description += '**Kayatan** ({0.mention}) - {1}\n'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['kayatan']), oshi_num.get('kayatan', 0))
    description += '**Myu** ({0.mention}) - {1}'.format(discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS['myu']), oshi_num.get('myu', 0))
    await bot.say(content='**Number of Users with Each WUG Member Role**', embed=create_embed(description=description))

@bot.command()
async def mv(*, song_name : str):
    name_to_mv = {}
    for mv, names in list(MV_NAMES.items()):
      name_to_mv.update({name : mv for name in names})

    if song_name.lower() in name_to_mv:
        await bot.say(MUSICVIDEOS[name_to_mv[song_name.lower()]])
    else:
        await bot.say(embed=create_embed(description='Couldn\'t find that MV. Use **!mv-list** to show the list of available MVs.', colour=discord.Colour.red()))

@bot.command(name='mv-list')
async def mv_list():
    description = '{0}\n\n'.format('\n'.join(list(MUSICVIDEOS.keys())))
    description += 'Use **!mv** *song* to show the full MV. You can also write the name of the song in English.'
    await bot.say(content='**List of Available Music Videos**', embed=create_embed(description=description))

@bot.command()
async def currency(*conversion : str):
    if len(conversion) == 4 and conversion[2].lower() == 'to':
        try:
            result = CurrencyRates().convert(conversion[1].upper(), conversion[3].upper(), Decimal(conversion[0]))
            await bot.say(embed=create_embed(title='{0} {1}'.format(('{:f}'.format(result)).rstrip('0').rstrip('.'), conversion[3].upper())))
            return
        except: pass
    await bot.say(embed=create_embed(description='Couldn\'t convert. Please follow this format for converting currency: **!currency** 12.34 AUD to USD.', colour=discord.Colour.red()))

@bot.command()
async def weather(*, location : str):
    query = location.split(',')
    if len(query) > 1:
        try:
            query[1] = pycountry.countries.get(name=query[1].strip().title()).alpha_2
        except: pass
    try:
        result = requests.get('http://api.openweathermap.org/data/2.5/weather', params={'q': ','.join(query), 'APPID': args.weather_api_key}).json()
        timezone = pytz.timezone(TimezoneFinder().timezone_at(lat=result['coord']['lat'], lng=result['coord']['lon']))
        description = 'Weather: {0}\n'.format(result['weather'][0]['description'].title())
        description += 'Temperature: {0} °C, {1} °F\n'.format('{0:.2f}'.format(float(result['main']['temp']) - 273.15), '{0:.2f}'.format(1.8 * (float(result['main']['temp']) - 273.15) + 32.0))
        description += 'Humidity: {0}%\n'.format(result['main']['humidity'])
        description += 'Wind Speed: {0} m/s\n'.format(result['wind']['speed'])
        description += 'Pressure: {0} hPa\n'.format(result['main']['pressure'])
        description += 'Sunrise: {0:%I}:{0:%M} {0:%p}\n'.format(datetime.fromtimestamp(result['sys']['sunrise'], tz=timezone))
        description += 'Sunset: {0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunset'], tz=timezone))
        await bot.say(content='**Weather for {0}, {1}**'.format(result['name'], pycountry.countries.lookup(result['sys']['country']).name), embed=create_embed(description=description))
        return
    except: pass
    await bot.say(embed=create_embed(description='Couldn\'t get weather. Please follow this format for checking the weather: **!weather** Melbourne, Australia.', colour=discord.Colour.red()))

@bot.command()
async def tagcreate(*, tag_to_create : str):
    split_request = tag_to_create.split()
    if len(split_request) > 1:
        tag_name = split_request[0]
        tag_content = tag_to_create[len(tag_name) + 1:]
        existing_tag = firebase.get('/tags', tag_name)
        if not existing_tag:
            firebase.patch('/tags', {tag_name: tag_content})
            await bot.say(content='Created Tag.', embed=create_embed(title=tag_name))
            await bot.say(tag_content)
        else:
            await bot.say(embed=create_embed(title='That tag already exists. Please choose a different tag name.', colour=discord.Colour.red()))
        return
    await bot.say(embed=create_embed(description='Couldn\'t create tag. Please follow this format for creating a tag: **!tagcreate** NameOfTag Content of the tag.', colour=discord.Colour.red()))

@bot.command()
async def tag(tag_name : str):
    tag_result = firebase.get('/tags', tag_name)
    if tag_result and len(tag_result) > 0:
        await bot.say(tag_result)
    else:
        await bot.say(embed=create_embed(description='That tag doesn\'t exist. Use **!tagcreate** to create a tag.', colour=discord.Colour.red()))

@bot.command()
async def choose(*options : str):
    if len(options) > 1:
        await bot.say(embed=create_embed(description=options[randrange(len(options))]))
    else:
        await bot.say(embed=create_embed(description='Please provide 2 or more options to choose from, e.g. **!choose** option1 option2.', colour=discord.Colour.red()))

def create_embed(title='', description='', colour=discord.Colour.default(), url='', fields={}, inline=False):
    embed = discord.Embed(title=title, description=description, colour=colour, url=url)
    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=inline)
    return embed

bot.loop.create_task(check_mute_status())
bot.run(args.token)