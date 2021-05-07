import hkdhelper as hkd
from discord.ext import commands
from discord_slash import cog_ext, SlashContext

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base="help",
        description="See detailed help for role commands.",
        guild_ids=hkd.get_all_guild_ids()
    )
    @commands.guild_only()
    async def roles(self, ctx: SlashContext):
        await ctx.defer()
        description = 'Users can have any of the 7 WUG member roles. Use the /oshihen command to get the role you want.\n\n'
        for oshi in hkd.WUG_ROLE_IDS:
            description += '**/oshihen** {0} for {1.mention}\n'.format(oshi.title(), hkd.get_wug_role(ctx.guild, oshi))
        description += "\nNote that using **/oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **/oshimashi** *member* instead. To get all 7 roles, use **/hakooshi**. Use **/kamioshi** *member* to specify which member you want to set as your highest role (you will get that member's colour).\n\n"
        description += 'Use **/oshi-count** to show the number of members with each WUG member role, or **/kamioshi-count** to show the number of members with each WUG member role as their highest role.\n'
        await ctx.send(content='**Commands for Roles**', embed=hkd.create_embed(description=description))

    @cog_ext.cog_subcommand(
        base="help",
        description="See detailed help for event commands.",
        guild_ids=hkd.get_all_guild_ids()
    )
    async def events(self, ctx: SlashContext):
        await ctx.defer()
        embed_fields = []
        embed_fields.append(('/events *date*', 'Get information for events involving WUG members on the specified date, e.g. **/events** apr 1. If *date* not specified, finds events happening today.'))
        embed_fields.append(('/eventsin *month* *member*', 'Get information for events involving WUG members for the specified month and member, e.g. **/eventsin** April Mayushii. If *member* not specified, searches for Wake, Up Girls! related events instead. Searches events from this month onwards only.'))
        await ctx.send(content='**Commands for Searching Events**', embed=hkd.create_embed(fields=embed_fields))
