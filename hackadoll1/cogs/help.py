import hkdhelper as hkd
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def help(self, ctx):
        await ctx.channel.trigger_typing()
        if ctx.invoked_subcommand is None:
            embed_fields = []
            embed_fields.append(('!help mod-commands', 'Show help for moderator-only commands.'))
            embed_fields.append(('!help roles', 'Show help for role commands.'))
            embed_fields.append(('!help events', 'Show help for event commands.'))
            embed_fields.append(('!help tags', 'Show help for tag commands.'))
            embed_fields.append(('!mv *song*', 'Show full MV of a song.'))
            embed_fields.append(('!mv-list', 'Show list of available MVs.'))
            embed_fields.append(('!userinfo', 'Show your user information.'))
            embed_fields.append(('!serverinfo', 'Show server information.'))
            embed_fields.append(('!tweetpics *url*', 'Get images from the specified tweet.'))
            embed_fields.append(('!blogpics *url*', 'Get images from the specified Ameba blog post.'))
            embed_fields.append(('!aichan-blogpics', 'Get images from the latest blog post by Aichan.'))
            embed_fields.append(('!tl *japanese text*', 'Translate the provided Japanese text into English via Google Translate.'))
            embed_fields.append(('!currency *amount* *x* to *y*', 'Convert *amount* of *x* currency to *y* currency, e.g. **!currency** 12.34 AUD to USD'))
            embed_fields.append(('!weather *city*, *country*', 'Show weather information for *city*, *country* (optional), e.g. **!weather** Melbourne, Australia'))
            embed_fields.append(('!choose *options*', 'Randomly choose from one of the provided options, e.g. **!choose** option1 option2'))
            embed_fields.append(('!yt *query*', 'Gets the top result from YouTube based on the provided search terms.'))
            embed_fields.append(('!dl-vid *url*', 'Attempts to download the video from the specified URL using youtube-dl.'))
            embed_fields.append(('!onmusu *member*', 'Show the Onsen Musume profile for the character of the specified member.'))
            await ctx.send(content='**Available Commands**', embed=hkd.create_embed(fields=embed_fields))

    @help.command(name='mod-commands', aliases=['mod', 'mods'])
    async def mod_commands(self, ctx):
        embed_fields = []
        embed_fields.append(('!kick *member*', 'Kick a member.'))
        embed_fields.append(('!ban *member*', 'Ban a member.'))
        embed_fields.append(('!mute *member* *duration*', 'Mute a member for *duration* minutes.'))
        embed_fields.append(('!unmute *member*', 'Unmute a member.'))
        await ctx.send(content='**Commands for Moderators**', embed=hkd.create_embed(fields=embed_fields))

    @help.command(aliases=['role'])
    @commands.guild_only()
    async def roles(self, ctx):
        description = 'Users can have any of the 7 WUG member roles. Use **!oshihen** *member* to get the role you want.\n\n'
        for oshi in hkd.WUG_ROLE_IDS:
            description += '**!oshihen** {0} for {1.mention}\n'.format(oshi.title(), hkd.get_wug_role(ctx.guild, oshi))
        description += "\nNote that using **!oshihen** will remove all of your existing member roles. To get an extra role without removing existing ones, use **!oshimashi** *member* instead. To get all 7 roles, use **!hakooshi**. Use **!kamioshi** *member* to specify which member you want to set as your highest role (you will get that member's colour).\n\n"
        description += 'Use **!oshi-count** to show the number of members with each WUG member role, or **!kamioshi-count** to show the number of members with each WUG member role as their highest role.\n'
        await ctx.send(content='**Commands for Roles**', embed=hkd.create_embed(description=description))

    @help.command(aliases=['event'])
    async def events(self, ctx):
        embed_fields = []
        embed_fields.append(('!events *date*', 'Get information for events involving WUG members on the specified date, e.g. **!events** apr 1. If *date* not specified, finds events happening today.'))
        embed_fields.append(('!eventsin *month* *member*', 'Get information for events involving WUG members for the specified month and member, e.g. **!eventsin** April Mayushii. If *member* not specified, searches for Wake, Up Girls! related events instead. Searches events from this month onwards only.'))
        await ctx.send(content='**Commands for Searching Events**', embed=hkd.create_embed(fields=embed_fields))

    @help.command(aliases=['tag'])
    async def tags(self, ctx):
        embed_fields = []
        embed_fields.append(('!tagcreate *tag_name* *content*', 'Create a tag. Use one word (no spaces) for tag names.'))
        embed_fields.append(('!tagupdate *tag_name* *updated_content*', 'Update an existing tag.'))
        embed_fields.append(('!tagdelete *tag_name*', 'Delete an existing tag.'))
        embed_fields.append(('!tagsearch', 'Shows a list of all existing tags.'))
        embed_fields.append(('!tag *tag_name*', 'Display a saved tag.'))
        await ctx.send(content='**Commands for Using Tags**', embed=hkd.create_embed(fields=embed_fields))
