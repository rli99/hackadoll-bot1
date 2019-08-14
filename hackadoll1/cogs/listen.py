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
        guild = disc_utils.get(self.bot.guilds, id=hkd.SERVER_ID)
        if member.guild == guild:
            channel = disc_utils.get(guild.channels, id=hkd.WELCOME_CHANNEL_ID)
            await channel.send(embed=hkd.create_embed(title='{0} ({1}) has left the server.'.format(member.display_name, member)))
