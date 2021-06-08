import discord
import hkdhelper as hkd
from discord import utils as disc_utils
from discord.ext import commands

class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('\n-------------\nLogged in as: {0} ({1})\n-------------\n'.format(self.bot.user.name, self.bot.user.id))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if (guild := hkd.get_wug_guild(self.bot.guilds)) == member.guild:
            channel = disc_utils.get(guild.channels, id=hkd.WELCOME_CHANNEL_ID)
            try:
                await member.guild.fetch_ban(member)
                return
            except discord.NotFound:
                await channel.send(embed=hkd.create_embed(title='{0} ({1}) has left the server.'.format(member.display_name, member)))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild == hkd.get_wug_guild(self.bot.guilds):
            for pattern in hkd.BANNED_USER_PATTERNS:
                if pattern.lower() in member.name.lower():
                    await member.ban()
