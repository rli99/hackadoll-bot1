import configparser

class Config():

    def __init__(self):
        config_parser = configparser.ConfigParser()
        config_parser.read('config.ini')
        config = config_parser['DEFAULT']
        self._SERVER_ID = int(config['SERVER_ID'])
        self._TEST_SERVER_ID = int(config['TEST_SERVER_ID'])
        self._TWITTER_CHANNEL_ID = int(config['TWITTER_CHANNEL_ID'])
        self._SEIYUU_CHANNEL_ID = int(config['SEIYUU_CHANNEL_ID'])
        self._WELCOME_CHANNEL_ID = int(config['WELCOME_CHANNEL_ID'])

    @property
    def SERVER_ID(self):
        return self._SERVER_ID
    
    @property
    def TEST_SERVER_ID(self):
        return self._TEST_SERVER_ID

    @property
    def TWITTER_CHANNEL_ID(self):
        return self._TWITTER_CHANNEL_ID

    @property
    def SEIYUU_CHANNEL_ID(self):
        return self._SEIYUU_CHANNEL_ID

    @property
    def WELCOME_CHANNEL_ID(self):
        return self._WELCOME_CHANNEL_ID

CONFIG = Config()
