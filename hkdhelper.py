import discord
from argparse import ArgumentParser

SERVER_ID = '280439975911096320'
MUTED_ROLE_ID = '445572638543446016'
WUG_ROLE_IDS = {'mayushii': '332788311280189443', 'aichan': '333727530680844288', 'minyami': '332793887200641028', 'yoppi': '332796755399933953', 'nanamin': '333721984196411392', 'kayatan': '333721510164430848', 'myu': '333722098377818115'}
MUSICVIDEOS = {'7 Girls War': 'https://streamable.com/1afp5', '言の葉 青葉': 'https://streamable.com/bn9mt', 'タチアガレ!': 'https://streamable.com/w85fh', '少女交響曲': 'https://streamable.com/gidqx', 'Beyond the Bottom': 'https://streamable.com/2ppw5', '僕らのフロンティア': 'https://streamable.com/pqydk', '恋?で愛?で暴君です!': 'https://streamable.com/88xas', 'One In A Billion': 'https://streamable.com/fa630', 'One In A Billion (Dance)': 'https://streamable.com/xbeeq', 'TUNAGO': 'https://streamable.com/4qjlp', '7 Senses': 'https://streamable.com/a34w9', '雫の冠': 'https://streamable.com/c6vfm', 'スキノスキル': 'https://streamable.com/w92kw'}
MV_NAMES = {'7 Girls War': ['7girlswar', '7gw'], '言の葉 青葉': ['言の葉青葉', 'kotonohaaoba'], 'タチアガレ!': ['tachiagare', 'タチアガレ'],  '少女交響曲': ['少女交響曲', 'skkk', 'shoujokkk', 'shoujo koukyoukyoku'], 'Beyond the Bottom': ['beyondthebottom', 'btb'], '僕らのフロンティア': ['僕らのフロンティア', 'bokufuro', '僕フロ', 'bokuranofrontier'], '恋?で愛?で暴君です!': ['恋で愛で暴君です', 'koiai', 'koideaideboukundesu', 'boukun', 'ででです'], 'One In A Billion': ['oneinabillion', 'oiab', 'ワンビリ'], 'One In A Billion (Dance)': ['oneinabilliondance', 'oiabdance', 'ワンビリdance'], 'TUNAGO': ['tunago'], '7 Senses': ['7senses'], '雫の冠': ['雫の冠', 'shizukunokanmuri'], 'スキノスキル': ['スキノスキル', 'sukinoskill']}
WUG_BLOG_ORDER = ['まゆ', 'μ', 'かやたん', 'anaminn', 'よぴ', 'みにゃみ', '永野愛理']
WUG_BLOG_SIGNS = {'mayushii': 'まゆ', 'myu': 'μ', 'kayatan': 'かやたん', 'nanamin': 'anaminn', 'yoppi': 'よぴ', 'minyami': 'みにゃみ', 'aichan': '永野愛理'}
WUG_MEMBERS = ['Wake Up, Girls', '吉岡茉祐', '永野愛理', '田中美海', '青山吉能', '山下七海', '奥野香耶', '高木美佑']

def parse_arguments():
    argparser = ArgumentParser(description='Discord bot for Wake Up, Girls! server.')
    argparser.add_argument('--token', required=True, help='Token for the discord app bot user.')
    argparser.add_argument('--firebase_credentials', required=True, metavar='DB_CRED', help='JSON file containing the credentials for the Firebase Realtime Database.')
    argparser.add_argument('--firebase_db', required=True, metavar='DB_URL', help='URL for the Firebase Realtime Database.')
    argparser.add_argument('--weather_api_key', required=True, metavar='KEY', help='API key for the OpenWeatherMap API.')
    return argparser.parse_args()

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

def create_embed(title='', description='', colour=discord.Colour.default(), url='', image='', thumbnail='', fields={}, inline=False):
    embed = discord.Embed(title=title, description=description, colour=colour, url=url)
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=inline)
    return embed

def strip_from_end(text, ending):
    if text.endswith(ending):
        return text[:-len(ending)]
    return text