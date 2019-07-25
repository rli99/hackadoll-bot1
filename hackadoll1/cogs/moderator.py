import time

from discord import Colour, Member
from discord.ext import commands
from hkdhelper import create_embed, get_muted_role
from humanfriendly import format_timespan

class Moderator(commands.Cog):
    def __init__(self, bot, firebase_ref):
        self.bot = bot
        self.firebase_ref = firebase_ref

    @commands.command()
    @commands.guild_only()
    async def kick(self, ctx, member: Member):
        await ctx.channel.trigger_typing()
        if ctx.author.guild_permissions.kick_members:
            if member.guild_permissions.administrator:
                await ctx.send(embed=create_embed(title='Moderators cannot be kicked.', colour=Colour.red()))
                return
            await member.kick()
            await ctx.send(embed=create_embed(title='{0} has been kicked.'.format(member)))
            self.firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
            return
        await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=Colour.red()))

    @commands.command()
    @commands.guild_only()
    async def ban(self, ctx, member: Member):
        await ctx.channel.trigger_typing()
        if ctx.author.guild_permissions.ban_members:
            await member.ban()
            await ctx.send(embed=create_embed(title='{0} has been banned.'.format(member)))
            self.firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
            return
        await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=Colour.red()))

    @commands.command()
    @commands.guild_only()
    async def mute(self, ctx, member: Member, duration: int):
        await ctx.channel.trigger_typing()
        if ctx.author.guild_permissions.kick_members:
            if member.guild_permissions.administrator:
                await ctx.send(embed=create_embed(title='Moderators cannot be muted.', colour=Colour.red()))
                return
            if duration > 0:
                mute_endtime = time.time() + duration * 60
                self.firebase_ref.child('muted_members/{0}'.format(member.id)).set(str(mute_endtime))
                muted_members[str(member.id)] = mute_endtime
                await member.add_roles(get_muted_role(ctx.guild))
                await ctx.send(embed=create_embed(description='{0.mention} has been muted for {1}.'.format(member, format_timespan(duration * 60))))
            else:
                await ctx.send(embed=create_embed(title='Please specify a duration greater than 0.', colour=Colour.red()))
        else:
            await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=Colour.red()))

    @commands.command()
    @commands.guild_only()
    async def unmute(self, ctx, member: Member):
        await ctx.channel.trigger_typing()
        if ctx.author.guild_permissions.kick_members:
            self.firebase_ref.child('muted_members/{0}'.format(member.id)).delete()
            muted_members.pop(member.id)
            await member.remove_roles(get_muted_role(ctx.guild))
            await ctx.send(embed=create_embed(description='{0.mention} has been unmuted.'.format(member)))
        else:
            await ctx.send(embed=create_embed(title='You do not have permission to do that.', colour=Colour.red()))