import asyncio

import hkdhelper as hkd
from discord import utils as disc_utils
from discord.ext import commands

class Secret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def say(self, ctx, channel_name: str, *, message: str):
        if ctx.author.id != hkd.BOT_ADMIN_ID:
            return
        guild = disc_utils.get(self.bot.guilds, id=hkd.SERVER_ID)
        channel = disc_utils.get(guild.channels, name=channel_name)
        await channel.trigger_typing()
        await asyncio.sleep(1.5)
        await channel.send(message)
