import time

import hkdhelper as hkd
from discord import Colour, Member, ChannelType
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option, create_permission
from humanfriendly import format_timespan

class Moderator(commands.Cog):
    def __init__(self, bot, muted_members, firebase_ref):
        self.bot = bot
        self.muted_members = muted_members
        self.firebase_ref = firebase_ref

    @cog_ext.cog_slash(
        description="[Moderator Only] Kick a member.",
        guild_ids=hkd.get_all_guild_ids(),
        default_permission=False,
        permissions={
            hkd.get_wug_server_id(): [
                create_permission(hkd.ADMIN_ID, SlashCommandPermissionType.ROLE, True)
            ]
        },
        options=[
            create_option(
                name="member",
                description="The member to kick.",
                option_type=6,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def kick(self, ctx: SlashContext, member: Member):
        await ctx.defer()
        if member.guild_permissions.administrator:
            await ctx.send(embed=hkd.create_embed(title='Moderators cannot be kicked.', colour=Colour.red()))
            return
        await member.kick()
        await ctx.send(embed=hkd.create_embed(title='{0} has been kicked.'.format(member)))
        self.firebase_ref.child('muted_members/{0}'.format(member.id)).delete()

    @cog_ext.cog_slash(
        description="[Moderator Only] Ban a member.",
        guild_ids=hkd.get_all_guild_ids(),
        default_permission=False,
        permissions={
            hkd.get_wug_server_id(): [
                create_permission(hkd.ADMIN_ID, SlashCommandPermissionType.ROLE, True)
            ]
        },
        options=[
            create_option(
                name="member",
                description="The member to ban.",
                option_type=6,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def ban(self, ctx: SlashContext, member: Member):
        await ctx.defer()
        if member.guild_permissions.administrator:
            await ctx.send(embed=hkd.create_embed(title='Moderators cannot be banned.', colour=Colour.red()))
            return
        await member.ban()
        await ctx.send(embed=hkd.create_embed(title='{0} has been banned.'.format(member)))
        self.firebase_ref.child('muted_members/{0}'.format(member.id)).delete()

    @cog_ext.cog_slash(
        description="[Moderator Only] Mute a member.",
        guild_ids=hkd.get_all_guild_ids(),
        default_permission=False,
        permissions={
            hkd.get_wug_server_id(): [
                create_permission(hkd.ADMIN_ID, SlashCommandPermissionType.ROLE, True)
            ]
        },
        options=[
            create_option(
                name="member",
                description="The member to mute.",
                option_type=6,
                required=True
            ),
            create_option(
                name="duration",
                description="The number of minutes to mute the member.",
                option_type=4,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def mute(self, ctx: SlashContext, member: Member, duration: int):
        await ctx.defer()
        if duration > 0:
            mute_endtime = time.time() + duration * 60
            self.firebase_ref.child('muted_members/{0}'.format(member.id)).set(str(mute_endtime))
            self.muted_members[str(member.id)] = mute_endtime
            await member.add_roles(hkd.get_muted_role(ctx.guild))
            await ctx.send(embed=hkd.create_embed(description='{0.mention} has been muted for {1}.'.format(member, format_timespan(duration * 60))))
        else:
            await ctx.send(embed=hkd.create_embed(title='Please specify a duration greater than 0.', colour=Colour.red()))

    @cog_ext.cog_slash(
        description="[Moderator Only] Unmute a member.",
        guild_ids=hkd.get_all_guild_ids(),
        default_permission=False,
        permissions={
            hkd.get_wug_server_id(): [
                create_permission(hkd.ADMIN_ID, SlashCommandPermissionType.ROLE, True)
            ]
        },
        options=[
            create_option(
                name="member",
                description="The member to unmute.",
                option_type=6,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def unmute(self, ctx: SlashContext, member: Member):
        await ctx.defer()
        self.firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
        self.muted_members.pop(member.id)
        await member.remove_roles(hkd.get_muted_role(ctx.guild))
        await ctx.send(embed=hkd.create_embed(description='{0.mention} has been unmuted.'.format(member)))

    @cog_ext.cog_slash(
        name="delete-messages",
        description="[Moderator Only] Delete messages from the current channel.",
        guild_ids=hkd.get_all_guild_ids(),
        default_permission=False,
        permissions={
            hkd.get_wug_server_id(): [
                create_permission(hkd.ADMIN_ID, SlashCommandPermissionType.ROLE, True)
            ]
        },
        options=[
            create_option(
                name="number",
                description="The number of messages to delete.",
                option_type=4,
                required=True
            ),
            create_option(
                name="member",
                description="The member from which to delete messages. If not specified, deletes from all messages.",
                option_type=6,
                required=False
            )
        ]
    )
    @commands.guild_only()
    async def delete_messages(self, ctx: SlashContext, number: int, member: Member = None):
        await ctx.defer()
        if ctx.channel.type == ChannelType.text:
            if not member:
                count = 0
                async for message in ctx.channel.history(limit=number + 1, oldest_first=False):
                    if count != 0:
                        await message.delete()
                    count += 1
                await ctx.send(embed=hkd.create_embed(description='{0} messages deleted.'.format(number)))
            else:
                count = 0
                messages_deleted = 0
                async for message in ctx.channel.history(limit=250, oldest_first=False):
                    if count != 0:
                        if message.author == member:
                            await message.delete()
                            messages_deleted += 1
                            if messages_deleted == number:
                                break
                    count += 1
                await ctx.send(embed=hkd.created_embed(description='{0} messages from {1.mention} deleted'.format(number, member)))
