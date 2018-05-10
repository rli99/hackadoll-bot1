import asyncio, discord, pycountry, pytz, requests, sys
from argparse import ArgumentParser
from datetime import datetime
from decimal import Decimal
from discord.ext import commands
from firebase import firebase
from forex_python.converter import CurrencyRates
from random import randrange
from timezonefinder import TimezoneFinder

def parse_arguments():
    parser = ArgumentParser(description='Discord bot for Wake Up, Girls! server.')
    parser.add_argument('--token', required=True, help='Token for the discord app bot user.')
    parser.add_argument('--firebase_db', required=True, metavar='DB_URL', help='URL for the Firebase Realtime Database.')
    parser.add_argument('--weather_api_key', required=True, metavar='KEY', help='API key for the OpenWeatherMap API.')
    return parser.parse_args()

WUG_ROLE_IDS = {'mayushii': '332788311280189443', 'aichan': '333727530680844288', 'minyami': '332793887200641028', 'yoppi': '332796755399933953', 'nanamin': '333721984196411392', 'kayatan': '333721510164430848', 'myu': '333722098377818115'}
MUSICVIDEOS = {'7 Girls War': 'https://streamable.com/1afp5', '言の葉 青葉': 'https://streamable.com/bn9mt', 'タチアガレ!': 'https://streamable.com/w85fh', '少女交響曲': 'https://streamable.com/gidqx', 'Beyond the Bottom': 'https://streamable.com/2ppw5', '僕らのフロンティア': 'https://streamable.com/aoa4z', '恋?で愛?で暴君です!': 'https://streamable.com/17myh', 'One In A Billion': 'https://streamable.com/fa630', 'One In A Billion (Dance)': 'https://streamable.com/xbeeq', 'TUNAGO': 'https://streamable.com/7flh7', '7 Senses': 'https://streamable.com/f8myx', '雫の冠': 'https://streamable.com/drggd', 'スキノスキル': 'https://streamable.com/w92kw'}
MV_NAMES = {'7 Girls War': ['7 girls war', '7gw'], '言の葉 青葉': ['言の葉 青葉', 'kotonoha aoba'], 'タチアガレ!': ['tachiagare!', 'タチアガレ!', 'tachiagare', 'タチアガレ'],  '少女交響曲': ['少女交響曲', 'skkk', 'shoujokkk', 'shoujo koukyoukyoku'], 'Beyond the Bottom': ['beyond the bottom', 'btb'], '僕らのフロンティア': ['僕らのフロンティア', 'bokufuro', '僕フロ', 'bokura no frontier'], '恋?で愛?で暴君です!': ['恋?で愛?で暴君です!', 'koiai', 'koi? de ai? de boukun desu!', 'koi de ai de boukun desu', 'boukun', 'ででです'], 'One In A Billion': ['one in a billion', 'oiab', 'ワンビリ'], 'One In A Billion (Dance)': ['one in a billion (dance)', 'oiab (dance)', 'ワンビリ (dance)', 'oiab dance'], 'TUNAGO': ['tunago'], '7 Senses': ['7 senses'], '雫の冠': ['雫の冠', 'shizuku no kanmuri'], 'スキノスキル': ['スキノスキル', 'suki no skill', 'sukinoskill']}

args = parse_arguments()
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
firebase = firebase.FirebaseApplication(args.firebase_db, None)

@bot.event
async def on_ready():
    print('\n-------------\nLogged in as: {0} ({1})\n-------------\n'.format(bot.user.name, bot.user.id))

@bot.command()
async def help():
    msg = '**Available Commands**\n\n'
    msg += '`!help`: Show this help message.\n\n'
    msg += '`!kick <member>`: Kick a member (mods only).\n'
    msg += '`!ban <member>`: Ban a member (mods only).\n\n'
    msg += '`!userinfo`: Show your user information.\n'
    msg += '`!serverinfo`: Show server information.\n\n'
    msg += '`!seiyuu-vids`: Show link to the wiki page with WUG seiyuu content.\n\n'
    msg += '`!oshihen <member>`: Change your oshi role.\n'
    msg += '`!oshimashi <member>`: Get an additional oshi role.\n'
    msg += '`!hakooshi`: Get all 7 WUG member roles.\n'
    msg += '`!roles`: Show additional help on how to get roles.\n'
    msg += '`!kamioshi-count`: Show the number of members with each WUG member role as their highest role.\n'
    msg += '`!oshi-count`: Show the number of members with each WUG member role.\n\n'
    msg += '`!mv <song>`: Show full MV of a song.\n'
    msg += '`!mv-list`: Show list of available MVs.\n\n'
    msg += '`!currency <amount> <x> to <y>`: Convert <amount> of <x> currency to <y> currency, e.g. `!currency 12.34 AUD to USD`.\n\n'
    msg += '`!weather <city>, <country>`: Show weather information for <city>, <country> (optional), e.g. `!weather Melbourne, Australia`.\n\n'
    msg += '`!tagcreate <tag_name> <content>`: Create a tag.\n'
    msg += '`!tag <tag_name>`: Display a saved tag.\n\n'
    msg += '`!choose <options>`: Randomly choose from one of the provided options, e.g. `!choose option1 option2`.'
    await bot.say(msg)

@bot.command(pass_context=True)
async def kick(ctx, member : discord.Member):
    if ctx.message.channel.permissions_for(ctx.message.author).kick_members:
        try:
            await bot.kick(member)
            await bot.say('{0.mention} has been kicked.'.format(member))
            return
        except: pass
    await bot.say('You do not have permission to do that.')

@bot.command(pass_context=True)
async def ban(ctx, member : discord.Member):
    if ctx.message.channel.permissions_for(ctx.message.author).ban_members:
        try:
            await bot.ban(member)
            await bot.say('{0.mention} has been banned.'.format(member))
            return
        except: pass
    await bot.say('You do not have permission to do that.')

@bot.command(pass_context=True)
async def userinfo(ctx):
    user = ctx.message.author
    msg = '**User Information for {0.mention}**\n\n'.format(user)
    msg += '**Name:** {0}\n'.format(user.display_name)
    msg += '**ID:** {0}\n'.format(user.id)
    msg += '**Joined server:** {0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC\n'.format(user.joined_at)
    msg += '**Account created:** {0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC\n'.format(user.created_at)
    msg += '**Roles:** {0}\n'.format(', '.join([r.name for r in user.roles[1:]]))
    msg += '**Avatar:** <{0}>'.format(user.avatar_url)
    await bot.say(msg)

@bot.command(pass_context=True)
async def serverinfo(ctx):
    server = ctx.message.server
    msg = '**Server Information**\n\n'
    msg += '**{0}** (ID: {1})\n'.format(server.name, server.id)
    msg += '**Owner:** {0} (ID: {1})\n'.format(server.owner, server.owner.id)
    msg += '**Members:** {0}\n'.format(server.member_count)
    msg += '**Channels:** {0} text, {1} voice\n'.format(sum(1 if str(channel.type) == 'text' else 0 for channel in server.channels), sum(1 if str(channel.type) == 'voice' else 0 for channel in server.channels))
    msg += '**Roles:** {0}\n'.format(len(server.roles))
    msg += '**Created on:** {0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC\n'.format(server.created_at)
    msg += '**Default channel:** {0}\n'.format(server.default_channel.name if server.default_channel is not None else '')
    msg += '**Region:** {0}\n'.format(server.region)
    msg += '**Icon:** <{0}>'.format(server.icon_url)
    await bot.say(msg)

@bot.command(name='seiyuu-vids')
async def seiyuu_vids():
    msg = '**WUG Seiyuu Videos**\n'
    msg += '<http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content>'
    await bot.say(msg)

@bot.command(pass_context=True)
async def oshihen(ctx, role_name : str):
    role = discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS[role_name.lower()])
    if role is None: 
        await bot.say('Couldn\'t find that role. Use `!roles` to show additional help on how to get roles.')
        return

    roles_to_remove = []
    for existing_role in ctx.message.author.roles:
        if str(existing_role.id) in WUG_ROLE_IDS.values():
            roles_to_remove.append(existing_role)

    if len(roles_to_remove) == 1 and roles_to_remove[0].name == role.name:
        await bot.say('Hello {0.message.author.mention}, you already have that role.'.format(ctx))
    elif len(roles_to_remove) > 0:
        await bot.remove_roles(ctx.message.author, *roles_to_remove)
        await asyncio.sleep(1)
        
    await bot.add_roles(ctx.message.author, role)
    await bot.say('Hello {0.message.author.mention}, you have oshihened to {1}.'.format(ctx, role_name.title()))

@bot.command(pass_context=True)
async def oshimashi(ctx, role_name : str):
    role = discord.utils.get(ctx.message.server.roles, id=WUG_ROLE_IDS[role_name.lower()])
    if role is None:
        await bot.say('Couldn\'t find that role. Use `!roles` to show additional help on how to get roles.')
        return

    if role not in ctx.message.author.roles:
        await bot.add_roles(ctx.message.author, role)
        await bot.say('Hello {0.message.author.mention}, you now have the {1} oshi role \'{2}\'.'.format(ctx, role_name.title(), role.name))
    else:
        await bot.say('Hello {0.message.author.mention}, you already have that role.'.format(ctx))

@bot.command(pass_context=True)
async def hakooshi(ctx):
    roles_to_add = []
    for role in ctx.message.server.roles:
        if role not in ctx.message.author.roles and str(role.id) in WUG_ROLE_IDS.values():
            roles_to_add.append(role)

    if len(roles_to_add) > 0:
        await bot.add_roles(ctx.message.author, *roles_to_add)
        await bot.say('Hello {0.message.author.mention}, you now have every WUG member role.'.format(ctx))
    else:
        await bot.say('Hello {0.message.author.mention}, you already have every WUG member role.'.format(ctx))

@bot.command(pass_context=True)
async def roles(ctx):
    ids_to_member = {v: k for k, v in WUG_ROLE_IDS.items()}
    member_to_role = {}
    for role in ctx.message.server.roles:
        if str(role.id) in ids_to_member:
            member_to_role[ids_to_member[role.id]] = role.name

    msg = '**How to get WUG Member Roles**\n\n'
    msg += 'Users can have any of the 7 WUG member roles. Use `!oshihen <member>` to get the role you want.\n\n'
    msg += '`!oshihen Mayushii` for \'{0}\' role\n'.format(member_to_role['mayushii'])
    msg += '`!oshihen Aichan` for \'{0}\' role\n'.format(member_to_role['aichan'])
    msg += '`!oshihen Minyami` for \'{0}\' role\n'.format(member_to_role['minyami'])
    msg += '`!oshihen Yoppi` for \'{0}\' role\n'.format(member_to_role['yoppi'])
    msg += '`!oshihen Nanamin` for \'{0}\' role\n'.format(member_to_role['nanamin'])
    msg += '`!oshihen Kayatan` for \'{0}\' role\n'.format(member_to_role['kayatan'])
    msg += '`!oshihen Myu` for \'{0}\' role\n\n'.format(member_to_role['myu'])
    msg += 'Note that using `!oshihen` will remove all of your existing member roles. To get an extra role without removing existing ones, use `!oshimashi <member>` instead. To get all 7 roles, use `!hakooshi`.'
    await bot.say(msg)

@bot.command(name='kamioshi-count', pass_context=True)
async def kamioshi_count(ctx):
    ids_to_member = {v: k for k, v in WUG_ROLE_IDS.items()}
    oshi_num = {}
    for member in ctx.message.server.members:
        member_roles = [r for r in member.roles if str(r.id) in ids_to_member]
        if len(member_roles) > 0:
            role = sorted(member_roles)[-1]
            if str(role.id) in ids_to_member:
                oshi_num[ids_to_member[str(role.id)]] = oshi_num.get(ids_to_member[str(role.id)], 0) + 1

    msg = '**Number of Users with Each WUG Member Role as Their Highest Role**\n\n'
    msg += 'Mayushii {0}\n'.format(oshi_num.get('mayushii', 0))
    msg += 'Aichan {0}\n'.format(oshi_num.get('aichan', 0))
    msg += 'Minyami {0}\n'.format(oshi_num.get('minyami', 0))
    msg += 'Yoppi {0}\n'.format(oshi_num.get('yoppi', 0))
    msg += 'Nanamin {0}\n'.format(oshi_num.get('nanamin', 0))
    msg += 'Kayatan {0}\n'.format(oshi_num.get('kayatan', 0))
    msg += 'Myu {0}\n'.format(oshi_num.get('myu', 0))
    await bot.say(msg)

@bot.command(name='oshi-count', pass_context=True)
async def oshi_count(ctx):
    ids_to_member = {v: k for k, v in WUG_ROLE_IDS.items()}
    oshi_num = {}
    for member in ctx.message.server.members:
        for role in member.roles:
            if str(role.id) in ids_to_member:
                oshi_num[ids_to_member[str(role.id)]] = oshi_num.get(ids_to_member[str(role.id)], 0) + 1

    msg = '**Number of Users with Each WUG Member Role**\n\n'
    msg += 'Mayushii {0}\n'.format(oshi_num.get('mayushii', 0))
    msg += 'Aichan {0}\n'.format(oshi_num.get('aichan', 0))
    msg += 'Minyami {0}\n'.format(oshi_num.get('minyami', 0))
    msg += 'Yoppi {0}\n'.format(oshi_num.get('yoppi', 0))
    msg += 'Nanamin {0}\n'.format(oshi_num.get('nanamin', 0))
    msg += 'Kayatan {0}\n'.format(oshi_num.get('kayatan', 0))
    msg += 'Myu {0}\n'.format(oshi_num.get('myu', 0))
    await bot.say(msg)

@bot.command()
async def mv(*, song_name : str):
    name_to_mv = {}
    for mv, names in list(MV_NAMES.items()):
      name_to_mv.update({name : mv for name in names})

    if song_name.lower() in name_to_mv:
        await bot.say(MUSICVIDEOS[name_to_mv[song_name.lower()]])
    else:
        await bot.say('Couldn\'t find that MV. Use `!mv-list` to show the list of available MVs.')

@bot.command(name='mv-list')
async def mv_list():
    msg = '**List of Available Music Videos**\n\n'
    msg += '{0}\n\n'.format('\n'.join(list(MUSICVIDEOS.keys())))
    msg += 'Use `!mv <song>` to show the full MV. You can also write the name of the song in English.'
    await bot.say(msg)

@bot.command()
async def currency(*conversion : str):
    if len(conversion) == 4 and conversion[2].lower() == 'to':
        try:
            result = CurrencyRates().convert(conversion[1].upper(), conversion[3].upper(), Decimal(conversion[0]))
            await bot.say('{0} {1}'.format(('{:f}'.format(result)).rstrip('0').rstrip('.'), conversion[3].upper()))
            return
        except: pass
    await bot.say('Couldn\'t convert. Please follow this format for converting currency: `!currency 12.34 AUD to USD`.')

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
        msg = '**Weather for {0}, {1}**\n\n'.format(result['name'], pycountry.countries.lookup(result['sys']['country']).name)
        msg += 'Weather: {0}\n'.format(result['weather'][0]['description'].title())
        msg += 'Temperature: {0} °C, {1} °F\n'.format('{0:.2f}'.format(float(result['main']['temp']) - 273.15), '{0:.2f}'.format(1.8 * (float(result['main']['temp']) - 273.15) + 32.0))
        msg += 'Humidity: {0}%\n'.format(result['main']['humidity'])
        msg += 'Wind Speed: {0} m/s\n'.format(result['wind']['speed'])
        msg += 'Pressure: {0} hPa\n'.format(result['main']['pressure'])
        msg += 'Sunrise: {0:%I}:{0:%M} {0:%p}\n'.format(datetime.fromtimestamp(result['sys']['sunrise'], tz=timezone))
        msg += 'Sunset: {0:%I}:{0:%M} {0:%p}\n'.format(datetime.fromtimestamp(result['sys']['sunset'], tz=timezone))
        await bot.say(msg)
        return
    except: pass
    await bot.say('Couldn\'t get weather. Please follow this format for checking the weather: `!weather Melbourne, Australia`.')

@bot.command()
async def tagcreate(*, tag_to_create : str):
    split_request = tag_to_create.split()
    if len(split_request) > 1:
        tag_name = split_request[0]
        tag_content = tag_to_create[len(tag_name) + 1:]
        existing_tag = firebase.get('/tags', tag_name)
        if not existing_tag:
            firebase.patch('/tags', {tag_name: tag_content})
            await bot.say('Created tag `{0}`\n\n{1}'.format(tag_name, tag_content))
        else:
            await bot.say('That tag already exists. Please choose a different tag name.')
        return
    await bot.say('Couldn\'t create tag. Please follow this format for creating a tag: `!createtag NameOfTag Content of the tag`.')

@bot.command()
async def tag(tag_name : str):
    tag_result = firebase.get('/tags', tag_name)
    if tag_result and len(tag_result) > 0:
        await bot.say(tag_result)
    else:
        await bot.say('That tag doesn\'t exist.')

@bot.command()
async def choose(*options : str):
    if len(options) > 1:
        await bot.say(options[randrange(len(options))])
    else:
        await bot.say('Please provide 2 or more options to choose from, e.g. `!choose option1 option2`.')

bot.run(args.token)