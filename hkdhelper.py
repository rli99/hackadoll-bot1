import configparser, discord, time
from dateutil import parser
from operator import itemgetter

SERVER_ID = '280439975911096320'
TWITTER_CHANNEL_ID = '448716340816248832'
MUTED_ROLE_ID = '445572638543446016'
WUG_ROLE_IDS = {'mayushii': '332788311280189443', 'aichan': '333727530680844288', 'minyami': '332793887200641028', 'yoppi': '332796755399933953', 'nanamin': '333721984196411392', 'kayatan': '333721510164430848', 'myu': '333722098377818115'}
MUSICVIDEOS = {'7 Girls War': 'https://streamable.com/1afp5', '言の葉 青葉': 'https://streamable.com/bn9mt', 'タチアガレ!': 'https://streamable.com/w85fh', '少女交響曲': 'https://streamable.com/gidqx', 'Beyond the Bottom': 'https://streamable.com/2ppw5', '僕らのフロンティア': 'https://streamable.com/pqydk', '恋?で愛?で暴君です!': 'https://streamable.com/88xas', 'One In A Billion': 'https://streamable.com/fa630', 'One In A Billion (Dance)': 'https://streamable.com/xbeeq', 'TUNAGO': 'https://streamable.com/4qjlp', '7 Senses': 'https://streamable.com/a34w9', '雫の冠': 'https://streamable.com/c6vfm', 'スキノスキル': 'https://streamable.com/w92kw'}
MV_NAMES = {'7 Girls War': ['7girlswar', '7gw'], '言の葉 青葉': ['言の葉青葉', 'kotonohaaoba'], 'タチアガレ!': ['tachiagare', 'タチアガレ'],  '少女交響曲': ['少女交響曲', 'skkk', 'shoujokkk', 'shoujo koukyoukyoku'], 'Beyond the Bottom': ['beyondthebottom', 'btb'], '僕らのフロンティア': ['僕らのフロンティア', 'bokufuro', '僕フロ', 'bokuranofrontier'], '恋?で愛?で暴君です!': ['恋で愛で暴君です', 'koiai', 'koideaideboukundesu', 'boukun', 'ででです'], 'One In A Billion': ['oneinabillion', 'oiab', 'ワンビリ'], 'One In A Billion (Dance)': ['oneinabilliondance', 'oiabdance', 'ワンビリdance'], 'TUNAGO': ['tunago'], '7 Senses': ['7senses'], '雫の冠': ['雫の冠', 'shizukunokanmuri'], 'スキノスキル': ['スキノスキル', 'sukinoskill']}
WUG_TWITTER_NAMES = ['wakeupgirls_PR', 'WUGch', 'wug_stage_2018', 'wugten']
WUG_TWITTER_BLOG_SIGNS = ['まゆ', 'あいり', '美海', 'よぴ', 'anaminn', 'かやたん', 'み´μ｀ゆ']
WUG_BLOG_ORDER = ['まゆ', 'μ', 'かやたん', 'anaminn', 'よぴ', 'みにゃみ', '永野愛理']
WUG_BLOG_SIGNS = {'mayushii': 'まゆ', 'myu': 'μ', 'kayatan': 'かやたん', 'nanamin': 'anaminn', 'yoppi': 'よぴ', 'minyami': 'みにゃみ', 'aichan': '永野愛理'}
WUG_MEMBERS = ['Wake Up, Girls', '吉岡茉祐', '永野愛理', '田中美海', '青山吉能', '山下七海', '奥野香耶', '高木美佑']
WUG_EVENTERNOTE_IDS = [6988, 3774, 6984, 6983, 6985, 6982, 6986, 6987]

def parse_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['DEFAULT']

def get_muted_role(server):
    return discord.utils.get(server.roles, id=MUTED_ROLE_ID)

def get_wug_role(server, member):
    return discord.utils.get(server.roles, id=WUG_ROLE_IDS[member.lower()])

def get_role_ids():
    return {v: k for k, v in WUG_ROLE_IDS.items()}

def parse_mv_name(name):
    for char in ' .,。、!?！？()（）':
        name = name.replace(char, '')
    return name.lower()

def parse_month(month):
    month_query = month.title()
    for i, month_group in enumerate(parser.parserinfo.MONTHS):
        if month_query in month_group:
            return str(i + 1) if i > 8 else '0{0}'.format(i + 1)
    return 'None'

def strip_from_end(text, endings):
    removing = True
    while removing:
        text = text.strip()
        removing = False
        for ending in endings:
            while text.endswith(ending):
                removing = True
                text = text[:-len(ending)]
    return text

def create_embed(author = {}, title='', description='', colour=discord.Colour.light_grey(), url='', image='', thumbnail='', fields=[], inline=False):
    embed = discord.Embed(title=title, description=description, colour=colour, url=url)
    if author:
        embed.set_author(name=author['name'], url=author['url'], icon_url=author['icon_url'])
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=inline)
    return embed

class Poll:
    def __init__(self):
        self.topic = ''
        self.owner = -1
        self.duration = -1
        self.topic_set_time = -1
        self.end_time = -1
        self.channel_id = -1
        self.options = []
        self.votes = {}

    def create(self, topic, owner, duration, channel_id):
        self.topic = topic
        self.owner = owner
        self.duration = duration
        self.channel_id = channel_id
        self.topic_set_time = time.time()

    def set_options(self, options, end_time):
        self.options = options
        self.end_time = end_time

    def get_details(self):
        details = ''
        for i, option in enumerate(self.options):
            details += '**{0}**   {1}{2}\n'.format(i + 1, ' ' if i < 9 else '', option)
        return details

    def end(self):
        results = {}
        for i, option in enumerate(self.options):
            results[option] = len(self.votes.get(i + 1, []))
        result_string = ''
        for result in sorted(results.items(), key=itemgetter(1), reverse=True):
            result_string += '{0} - {1} vote{2}\n'.format(result[0], result[1], '' if result[1] == 1 else 's')
        self.reset()
        return result_string

    def vote(self, option, voter_id):
        current_votes = self.votes.get(option, [])
        if voter_id not in current_votes:
            current_votes.append(voter_id)
            self.votes[option] = current_votes

    def check_status(self):
        topic = self.topic
        channel = self.channel_id
        if self.options and time.time() > self.end_time:
            return (topic, channel, self.end())
        if self.topic and not self.options and time.time() > self.topic_set_time + 240:
            self.reset()
            return ('', channel, '')
        return ('', '', '')

    def reset(self):
        self.topic = ''
        self.options = []
        self.votes = {}