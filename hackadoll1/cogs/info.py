import hkdhelper as hkd
from discord import Member
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        description="Show details of the specified member, or your own details if not specified.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="member",
                description="The member to show details for.",
                option_type=6,
                required=False
            )
        ]
    )
    @commands.guild_only()
    async def userinfo(self, ctx: SlashContext, member: Member = None):
        await ctx.defer()
        user = member or ctx.author
        embed_fields = []
        embed_fields.append(('Name', '{0}'.format(user.display_name)))
        embed_fields.append(('ID', '{0}'.format(user.id)))
        embed_fields.append(('Joined Server', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(user.joined_at)))
        embed_fields.append(('Account Created', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(user.created_at)))
        embed_fields.append(('Roles', '{0}'.format(', '.join([r.name for r in user.roles[1:]]) if user.roles[1:] else 'None')))
        embed_fields.append(('Avatar', '{0}'.format('<{0}>'.format(user.avatar_url) if user.avatar_url else 'None')))
        await ctx.send(content='**User Information for {0.mention}**'.format(user), embed=hkd.create_embed(fields=embed_fields, inline=True))

    @cog_ext.cog_slash(
        description="Show server information.",
        guild_ids=hkd.get_all_guild_ids(),
    )
    @commands.guild_only()
    async def serverinfo(self, ctx: SlashContext):
        await ctx.defer()
        guild = ctx.guild
        embed_fields = []
        embed_fields.append(('{0}'.format(guild.name), '(ID: {0})'.format(guild.id)))
        embed_fields.append(('Owner', '{0} (ID: {1})'.format(guild.owner, guild.owner.id)))
        embed_fields.append(('Members', '{0}'.format(guild.member_count)))
        embed_fields.append(('Channels', '{0} text, {1} voice'.format(len(guild.text_channels), len(guild.voice_channels))))
        embed_fields.append(('Roles', '{0}'.format(len(guild.roles))))
        embed_fields.append(('Created On', '{0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S} UTC'.format(guild.created_at)))
        embed_fields.append(('Region', '{0}'.format(guild.region)))
        embed_fields.append(('Icon', '{0}'.format('<{0}>'.format(guild.icon_url) if guild.icon_url else 'None')))
        await ctx.send(content='**Server Information**', embed=hkd.create_embed(fields=embed_fields, inline=True))
