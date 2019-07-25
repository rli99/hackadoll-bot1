import hkdhelper as hkd

from discord import Colour
from discord.ext import commands
from hkdhelper import create_embed

class MV(commands.Cog):
    def __init__(self, bot, firebase_ref):
        self.bot = bot
        self.firebase_ref = firebase_ref

    @commands.command()
    async def mv(self, ctx, *, song_name: str):
        await ctx.channel.trigger_typing()
        name_to_mv = {}
        for mv, names in list(self.firebase_ref.child('music_videos/mv_aliases').get().items()):
            name_to_mv.update({name: mv for name in names})
        song = hkd.parse_mv_name(song_name)
        if song in name_to_mv:
            await ctx.send(self.firebase_ref.child('music_videos/mv_links').get()[name_to_mv[song]])
        else:
            await ctx.send(embed=create_embed(description="Couldn't find that MV. Use **!mv-list** to show the list of available MVs.", colour=Colour.red()))

    @commands.command(name='mv-list', aliases=['mvlist', 'mvs'])
    async def mv_list(self, ctx):
        await ctx.channel.trigger_typing()
        description = '{0}\n\n'.format('\n'.join(list(self.firebase_ref.child('music_videos/mv_links').get().keys())))
        description += 'Use **!mv** *song* to show the full MV. You can also write the name of the song in English.'
        await ctx.send(content='**List of Available Music Videos**', embed=create_embed(description=description))