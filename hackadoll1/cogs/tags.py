import hkdhelper as hkd
from discord import Colour
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

class Tags(commands.Cog):
    def __init__(self, bot, firebase_ref):
        self.bot = bot
        self.firebase_ref = firebase_ref

    @cog_ext.cog_subcommand(
        base="tag",
        description="Create a tag.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="name",
                description="Name of the tag, followed by the content of the tag.",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def create(self, ctx: SlashContext, name: str):
        await ctx.defer()
        if len(split_request := name.split()) > 1:
            tag_name = split_request[0]
            tag_content = name[len(tag_name) + 1:]
            if tag_name not in self.firebase_ref.child('tags').get():
                self.firebase_ref.child('tags/{0}'.format(tag_name)).set(tag_content)
                await ctx.send(embed=hkd.create_embed(title='Successfully created tag - {0}'.format(tag_name)))
            else:
                await ctx.send(embed=hkd.create_embed(title='That tag already exists. Please choose a different tag name.', colour=Colour.red()))
            return
        await ctx.send(embed=hkd.create_embed(description="Couldn't create tag.", colour=Colour.red()))

    @cog_ext.cog_subcommand(
        base="tag",
        description="Update a tag.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="name",
                description="Name of the tag, followed by the new content of the tag.",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def update(self, ctx: SlashContext, name: str):
        await ctx.defer()
        if len(split_update := name.split()) > 1:
            tag_name = split_update[0]
            updated_content = name[len(tag_name) + 1:]
            if tag_name in self.firebase_ref.child('tags').get():
                self.firebase_ref.child('tags/{0}'.format(tag_name)).set(updated_content)
                await ctx.send(embed=hkd.create_embed(title='Successfully updated tag - {0}.'.format(tag_name)))
            else:
                await ctx.send(embed=hkd.create_embed(title="That tag doesn't exist."))
            return
        await ctx.send(embed=hkd.create_embed(description="Couldn't update tag.", colour=Colour.red()))

    @cog_ext.cog_subcommand(
        base="tag",
        description="Delete a tag.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="name",
                description="Name of the tag to delete.",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def delete(self, ctx: SlashContext, name: str):
        await ctx.defer()
        if self.firebase_ref.child('tags/{0}'.format(name)).get():
            self.firebase_ref.child('tags/{0}'.format(name)).delete()
            await ctx.send(embed=hkd.create_embed(title='Successfully removed tag - {0}.'.format(name)))
        else:
            await ctx.send(embed=hkd.create_embed(title="That tag doesn't exist.", colour=Colour.red()))

    @cog_ext.cog_subcommand(
        base="tag",
        description="Show a list of all existing tags.",
        guild_ids=hkd.get_all_guild_ids(),
    )
    @commands.guild_only()
    async def search(self, ctx: SlashContext):
        await ctx.defer()
        tag_list = self.firebase_ref.child('tags').get()
        await ctx.send(content='Existing Tags', embed=hkd.create_embed(title=', '.join(list(tag_list.keys()))))

    @cog_ext.cog_subcommand(
        base="tag",
        description="Get a tag.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="name",
                description="Name of the tag to show.",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def get(self, ctx: SlashContext, name: str):
        await ctx.defer()
        if tag_result := self.firebase_ref.child('tags/{0}'.format(name)).get():
            if not (split_tag := hkd.split_embeddable_content(tag_result)):
                await ctx.send(tag_result)
            else:
                await hkd.send_content_with_delay(ctx, split_tag)
        else:
            await ctx.send(embed=hkd.create_embed(description="That tag doesn't exist.", colour=Colour.red()))
