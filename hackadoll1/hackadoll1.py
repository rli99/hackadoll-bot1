import instaloader
import twitter
from apiclient.discovery import build
from discord.ext import commands
from firebase_admin import credentials, db, initialize_app
from hkdhelper import parse_config
from httplib2 import Http
from oauth2client import file

from cogs.help import Help
from cogs.mod import Moderator
from cogs.oshi import Oshi
from cogs.info import Info
from cogs.events import Events
from cogs.tags import Tags
from cogs.mv import MusicVideo
from cogs.pics import Pics
from cogs.misc import Misc
from cogs.secret import Secret
from cogs.listen import Listen
from cogs.loop import Loop

def main():
    config = parse_config()
    bot = commands.Bot(command_prefix=('!', 'ichigo ', 'alexa ', 'Ichigo ', 'Alexa '))
    bot.remove_command('help')
    certificate = credentials.Certificate(config['firebase_credentials'])
    initialize_app(certificate, {'databaseURL': config['firebase_db']})
    firebase_ref = db.reference()
    muted_members = firebase_ref.child('muted_members').get() or {}
    twitter_api = twitter.Api(consumer_key=config['consumer_key'], consumer_secret=config['consumer_secret'], access_token_key=config['access_token_key'], access_token_secret=config['access_token_secret'], tweet_mode='extended')
    insta_api = instaloader.Instaloader()
    insta_api.load_session_from_file(config['instagram_user'], filename='./.instaloader-session')
    calendar = build('calendar', 'v3', http=file.Storage('credentials.json').get().authorize(Http()))

    bot.add_cog(Help(bot))
    bot.add_cog(Moderator(bot, muted_members, firebase_ref))
    bot.add_cog(Oshi(bot))
    bot.add_cog(Info(bot))
    bot.add_cog(Events(bot))
    bot.add_cog(Tags(bot, firebase_ref))
    bot.add_cog(MusicVideo(bot, firebase_ref))
    bot.add_cog(Pics(bot, twitter_api))
    bot.add_cog(Misc(bot, config))
    bot.add_cog(Secret(bot, firebase_ref, twitter_api))
    bot.add_cog(Loop(bot, config, muted_members, firebase_ref, calendar, twitter_api, insta_api))
    bot.add_cog(Listen(bot))

    bot.run(config['token'])

if __name__ == '__main__':
    main()
