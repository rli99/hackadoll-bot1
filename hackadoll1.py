import discord
import asyncio
import sys

WUG_ROLE_IDS = { 'mayushii': '332788311280189443', 'aichan': '333727530680844288', 'minyami': '332793887200641028', 'yoppi': '332796755399933953', 'nanamin': '333721984196411392', 'kayatan': '333721510164430848', 'myu': '333722098377818115' }

MUSICVIDEOS = { '7 Girls War': 'https://streamable.com/1afp5', '言の葉 青葉': 'https://streamable.com/bn9mt', 'タチアガレ!': 'https://streamable.com/w85fh', '少女交響曲': 'https://streamable.com/gidqx', 'Beyond the Bottom': 'https://streamable.com/2ppw5', '僕らのフロンティア': 'https://streamable.com/aoa4z', '恋?で愛?で暴君です!': 'https://streamable.com/17myh', 'TUNAGO': 'https://streamable.com/7flh7', '7 Senses': 'https://streamable.com/f8myx', '雫の冠': 'https://streamable.com/drggd', 'スキノスキル': 'https://streamable.com/w92kw' }

MV_NAMES = { '7 Girls War': ['7 girls war', '7gw'], '言の葉 青葉': ['言の葉 青葉', 'kotonoha aoba'], 'タチアガレ!': ['タチアガレ!', 'tachiagare', 'タチアガレ'],  '少女交響曲': ['少女交響曲', 'skkk', 'shoujokkk', 'shoujo koukyoukyoku'], 'Beyond the Bottom': ['beyond the bottom', 'btb'], '僕らのフロンティア': ['僕らのフロンティア', 'bokufuro', '僕フロ', 'bokura no frontier'], '恋?で愛?で暴君です!': ['恋?で愛?で暴君です!', 'koiai', 'koi? de ai? de boukun desu!', 'koi de ai de boukun desu', 'boukun', 'ででです'], 'TUNAGO': ['tunago'], '7 Senses': ['7 senses'], '雫の冠': ['雫の冠', 'shizuku no kanmuri'], 'スキノスキル': ['スキノスキル', 'suki no skill', 'sukinoskill'] }

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    commands = { '!help': help_message, '!userinfo': show_userinfo, '!serverinfo': show_serverinfo, '!seiyuu-vids': seiyuu_vids, '!hakooshi': hakooshi, '!roles': role_help, '!kamioshi-count': kamioshi_count, '!oshi-count': oshi_count, '!mv-list': show_mv_list }

    if message.content in commands:
        await commands[message.content](message)
    elif message.content.startswith('!kick '):
        await kick_member(message)
    elif message.content.startswith('!ban '):
        await ban_member(message)
    elif message.content.startswith('!oshihen '):
        await oshihen(message)
    elif message.content.startswith('!oshimashi '):
        await oshimashi(message)
    elif message.content.startswith('!mv '):
        await show_mv(message)

@client.event
async def help_message(message):
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
    msg += '`!mv-list`: Show list of available MVs.'
    await client.send_message(message.channel, msg)

@client.event
async def kick_member(message):
    if len(message.mentions) > 0:
        member = message.mentions[0]
        if message.channel.permissions_for(message.author).kick_members:
            await client.kick(member)
            msg = '{0.mention} has been kicked.'.format(member)
            await client.send_message(message.channel, msg)
        else:
            msg = 'You do not have permission to do that.'
            await client.send_message(message.channel, msg)

@client.event
async def ban_member(message):
    if len(message.mentions) > 0:
        member = message.mentions[0]
        if message.channel.permissions_for(message.author).ban_members:
            await client.ban(member)
            msg = '{0.mention} has been banned.'.format(member)
            await client.send_message(message.channel, msg)
        else:
            msg = 'You do not have permission to do that.'
            await client.send_message(message.channel, msg)

@client.event
async def show_userinfo(message):
    user = message.author
    msg = '**User Information for {0.mention}**\n\n'.format(user)
    msg += '**Name:** {0}\n'.format(user.display_name)
    msg += '**ID:** {0}\n'.format(user.id)
    msg += '**Joined server:** {0} UTC\n'.format(user.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
    msg += '**Account created:** {0} UTC\n'.format(user.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    msg += '**Roles:** {0}\n'.format(', '.join([r.name for r in user.roles[1:]]))
    msg += '**Avatar:** <{0}>'.format(user.avatar_url)
    await client.send_message(message.channel, msg)

@client.event
async def show_serverinfo(message):
    server = message.server
    msg = '**Server Information**\n\n'
    msg += '**{0}** (ID: {1})\n'.format(server.name, server.id)
    msg += '**Owner:** {0} (ID: {1})\n'.format(server.owner, server.owner.id)
    msg += '**Members:** {0}\n'.format(server.member_count)
    msg += '**Channels:** {0} text, {1} voice\n'.format(sum(1 if str(channel.type) == 'text' else 0 for channel in server.channels), sum(1 if str(channel.type) == 'voice' else 0 for channel in server.channels))
    msg += '**Roles:** {0}\n'.format(len(server.roles))
    msg += '**Created on:** {0} UTC\n'.format(server.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    msg += '**Default channel:** {0}\n'.format(server.default_channel.name if server.default_channel is not None else '')
    msg += '**Region:** {0}\n'.format(server.region)
    msg += '**Icon:** <{0}>'.format(server.icon_url)
    await client.send_message(message.channel, msg)

@client.event
async def seiyuu_vids(message):
    msg = '**WUG Seiyuu Videos**\n'
    msg += '<http://wake-up-girls.wikia.com/wiki/List_of_Seiyuu_Content>'
    await client.send_message(message.channel, msg)

@client.event
async def oshihen(message):
    role_name = message.content[9:]
    role = discord.utils.get(message.server.roles, id=WUG_ROLE_IDS[role_name.lower()])

    roles_to_remove = []
    for existing_role in message.author.roles:
        if str(existing_role.id) in WUG_ROLE_IDS.values():
            roles_to_remove.append(existing_role)

    if len(roles_to_remove) == 1 and roles_to_remove[0].name == role.name:
        msg = 'Hello {0.author.mention}, you already have that role.'.format(message)
        await client.send_message(message.channel, msg)
        return;

    if len(roles_to_remove) > 0:
        await client.remove_roles(message.author, *roles_to_remove)
        await asyncio.sleep(1)

    if role is not None:
        await client.add_roles(message.author, role)
        msg = 'Hello {0.author.mention}, you have oshihened to {1}.'.format(message, role_name.title())
        await client.send_message(message.channel, msg)

@client.event
async def oshimashi(message):
    role_name = message.content[11:]
    role = discord.utils.get(message.server.roles, id=WUG_ROLE_IDS[role_name.lower()])

    if role is not None:
        if role not in message.author.roles:
            await client.add_roles(message.author, role)
            msg = 'Hello {0.author.mention}, you now have the {1} oshi role \'{2}\'.'.format(message, role_name.title(), role.name)
            await client.send_message(message.channel, msg)
        else:
            msg = 'Hello {0.author.mention}, you already have that role.'.format(message)
            await client.send_message(message.channel, msg)

@client.event
async def hakooshi(message):
    roles_to_add = []
    for role in message.server.roles:
        if role not in message.author.roles and str(role.id) in WUG_ROLE_IDS.values():
            roles_to_add.append(role)

    if len(roles_to_add) > 0:
        await client.add_roles(message.author, *roles_to_add)
        msg = 'Hello {0.author.mention}, you now have every WUG member role.'.format(message)
        await client.send_message(message.channel, msg)
    else:
        msg = 'Hello {0.author.mention}, you already have every WUG member role.'.format(message)
        await client.send_message(message.channel, msg)

@client.event
async def role_help(message):
    ids_to_member = { v: k for k, v in WUG_ROLE_IDS.items() }
    member_to_role = {}

    for role in message.server.roles:
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
    await client.send_message(message.channel, msg)

@client.event
async def kamioshi_count(message):
    ids_to_member = { v: k for k, v in WUG_ROLE_IDS.items() }
    oshi_num = {}

    for member in message.server.members:
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
    await client.send_message(message.channel, msg)

@client.event
async def oshi_count(message):
    ids_to_member = { v: k for k, v in WUG_ROLE_IDS.items() }
    oshi_num = {}

    for member in message.server.members:
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
    await client.send_message(message.channel, msg)

@client.event
async def show_mv(message):
    song_name = message.content[4:].lower()
    name_to_mv = {}

    for mv, names in list(MV_NAMES.items()):
      name_to_mv.update({ name : mv for name in names })

    if song_name in name_to_mv:
        msg = MUSICVIDEOS[name_to_mv[song_name]]
        await client.send_message(message.channel, msg)

@client.event
async def show_mv_list(message):
    msg = '**List of Available Music Videos**\n\n'
    msg += '{0}\n\n'.format('\n'.join(list(MUSICVIDEOS.keys())))
    msg += 'Use `!mv <song>` to show the full MV. You can also write the name of the song in English.'
    await client.send_message(message.channel, msg)

client.run(sys.argv[1])