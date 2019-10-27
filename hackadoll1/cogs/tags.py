import hkdhelper as hkd
from discord import Colour
from discord.ext import commands

class Tags(commands.Cog):
    def __init__(self, bot, firebase_ref):
        self.bot = bot
        self.firebase_ref = firebase_ref

    @commands.command(aliases=['createtag'])
    @commands.guild_only()
    async def tagcreate(self, ctx, *, tag_to_create: str):
        await ctx.channel.trigger_typing()
        if len(split_request := tag_to_create.split()) > 1:
            tag_name = split_request[0]
            tag_content = tag_to_create[len(tag_name) + 1:]
            if tag_name not in self.firebase_ref.child('tags').get():
                self.firebase_ref.child('tags/{0}'.format(tag_name)).set(tag_content)
                await ctx.send(embed=hkd.create_embed(title='Successfully created tag - {0}'.format(tag_name)))
            else:
                await ctx.send(embed=hkd.create_embed(title='That tag already exists. Please choose a different tag name.', colour=Colour.red()))
            return
        await ctx.send(embed=hkd.create_embed(description="Couldn't create tag. Please follow this format for creating a tag: **!tagcreate** *NameOfTag* *Content of the tag*.", colour=Colour.red()))

    @commands.command(aliases=['updatetag'])
    @commands.guild_only()
    async def tagupdate(self, ctx, *, tag_to_update: str):
        await ctx.channel.trigger_typing()
        if len(split_update := tag_to_update.split()) > 1:
            tag_name = split_update[0]
            updated_content = tag_to_update[len(tag_name) + 1:]
            if tag_name in self.firebase_ref.child('tags').get():
                self.firebase_ref.child('tags/{0}'.format(tag_name)).set(updated_content)
                await ctx.send(embed=hkd.create_embed(title='Successfully updated tag - {0}.'.format(tag_name)))
            else:
                await ctx.send(embed=hkd.create_embed(title="That tag doesn't exist."))
            return
        await ctx.send(embed=hkd.create_embed(description="Couldn't update tag. Please follow this format for updating a tag: **!tagupdate** *NameOfTag* *Updated content of the tag*.", colour=Colour.red()))

    @commands.command(aliases=['tagremove', 'deletetag', 'removetag'])
    @commands.guild_only()
    async def tagdelete(self, ctx, tag_name: str):
        await ctx.channel.trigger_typing()
        if self.firebase_ref.child('tags/{0}'.format(tag_name)).get():
            self.firebase_ref.child('tags/{0}'.format(tag_name)).delete()
            await ctx.send(embed=hkd.create_embed(title='Successfully removed tag - {0}.'.format(tag_name)))
        else:
            await ctx.send(embed=hkd.create_embed(title="That tag doesn't exist.", colour=Colour.red()))

    @commands.command(aliases=['searchtag', 'tags'])
    @commands.guild_only()
    async def tagsearch(self, ctx):
        await ctx.channel.trigger_typing()
        tag_list = self.firebase_ref.child('tags').get()
        await ctx.send(content='Existing Tags', embed=hkd.create_embed(title=', '.join(list(tag_list.keys()))))

    @commands.command()
    @commands.guild_only()
    async def tag(self, ctx, tag_name: str):
        await ctx.channel.trigger_typing()
        if tag_result := self.firebase_ref.child('tags/{0}'.format(tag_name)).get():
            if not (split_tag := hkd.split_embeddable_content(tag_result)):
                await ctx.send(tag_result)
            else:
                await hkd.send_content_with_delay(ctx, split_tag)
        else:
            await ctx.send(embed=hkd.create_embed(description="That tag doesn't exist. Use **!tagcreate** *tag_name* *Content of the tag* to create a tag.", colour=Colour.red()))
