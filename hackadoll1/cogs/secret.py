import asyncio, discord
import hkdhelper as hkd

from discord.ext import commands

class Secret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('\n-------------\nLogged in as: {0} ({1})\n-------------\n'.format(self.bot.user.name, self.bot.user.id))

    @commands.command()
    async def say(self, ctx, channel_name: str, *, message: str):
        if ctx.author.id != hkd.BOT_ADMIN_ID:
            return
        guild = discord.utils.get(self.bot.guilds, id=hkd.SERVER_ID)
        channel = discord.utils.get(guild.channels, name=channel_name)
        await channel.trigger_typing()
        await asyncio.sleep(1.5)
        await channel.send(message)