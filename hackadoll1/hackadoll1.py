import discord
import twitter
from apiclient.discovery import build
from discord.ext import commands
from discord_slash import SlashCommand
from firebase_admin import credentials, db, initialize_app
from hkdhelper import parse_config
from httplib2 import Http
from oauth2client import file

from cogs.help import Help
from cogs.oshi import Oshi
from cogs.info import Info
from cogs.events import Events
from cogs.tags import Tags
from cogs.pics import Pics
from cogs.misc import Misc
from cogs.listen import Listen
from cogs.loop import Loop

def main():
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

    config = parse_config()
    certificate = credentials.Certificate(config['firebase_credentials'])
    initialize_app(certificate, {'databaseURL': config['firebase_db']})
    firebase_ref = db.reference()
    twitter_api = twitter.Api(consumer_key=config['consumer_key'], consumer_secret=config['consumer_secret'], access_token_key=config['access_token_key'], access_token_secret=config['access_token_secret'], tweet_mode='extended')
    calendar = build('calendar', 'v3', http=file.Storage('credentials.json').get().authorize(Http()))

    bot.add_cog(Help(bot))
    bot.add_cog(Oshi(bot))
    bot.add_cog(Info(bot))
    bot.add_cog(Events(bot))
    bot.add_cog(Tags(bot, firebase_ref))
    bot.add_cog(Pics(bot, twitter_api))
    bot.add_cog(Misc(bot, config))
    bot.add_cog(Loop(bot, config, firebase_ref, calendar, twitter_api))
    bot.add_cog(Listen(bot))

    bot.run(config['token'])

if __name__ == '__main__':
    main()
