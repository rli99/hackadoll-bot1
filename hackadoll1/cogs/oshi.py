import asyncio, discord
import hkdhelper as hkd

from discord import Colour
from discord.ext import commands
from hkdhelper import create_embed, dict_reverse, get_wug_role
from operator import itemgetter

class Oshi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def oshihen(self, ctx, member: str=''):
        await ctx.channel.trigger_typing()
        role = get_wug_role(ctx.guild, member)
        if role is None:
            await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=Colour.red()))
            return
        roles_to_remove = []
        for existing_role in ctx.author.roles:
            if existing_role.id in hkd.WUG_ROLE_IDS.values() or existing_role.id in hkd.WUG_KAMIOSHI_ROLE_IDS.values():
                roles_to_remove.append(existing_role)
        if len(roles_to_remove) == 1 and roles_to_remove[0].name == role.name:
            await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=Colour.red()))
        elif len(roles_to_remove) > 0:
            await ctx.author.remove_roles(*roles_to_remove)
            await asyncio.sleep(1)
        await ctx.author.add_roles(role)
        await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you have oshihened to the **{1}** role {2.mention}.'.format(ctx, member.title(), role), colour=role.colour))

    @commands.command()
    @commands.guild_only()
    async def oshimashi(self, ctx, member: str=''):
        await ctx.channel.trigger_typing()
        role = get_wug_role(ctx.guild, member)
        if role is None:
            await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=Colour.red()))
            return
        if role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you now have the **{1}** oshi role {2.mention}.'.format(ctx, member.title(), role), colour=role.colour))
        else:
            await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have that role.'.format(ctx), colour=Colour.red()))

    @commands.command()
    @commands.guild_only()
    async def hakooshi(self, ctx):
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
            await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you now have every WUG member role.'.format(ctx), colour=Colour.teal()))
        else:
            await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, you already have every WUG member role.'.format(ctx), colour=Colour.red()))

    @commands.command()
    @commands.guild_only()
    async def kamioshi(self, ctx, member: str=''):
        await ctx.channel.trigger_typing()
        role = get_wug_role(ctx.guild, member)
        if role is None:
            await ctx.send(embed=create_embed(description="Couldn't find that role. Use **!help roles** to show additional help on how to get roles.", colour=Colour.red()))
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
            await ctx.send(embed=create_embed(description='Hello {0.message.author.mention}, that member is already your kamioshi.'.format(ctx), colour=Colour.red()))

    @commands.command(name='kamioshi-count', aliases=['kamioshicount'])
    @commands.guild_only()
    async def kamioshi_count(self, ctx):
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

    @commands.command(name='oshi-count', aliases=['oshicount'])
    @commands.guild_only()
    async def oshi_count(self, ctx):
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