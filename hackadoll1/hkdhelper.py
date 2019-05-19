import configparser, discord, time
from bs4 import BeautifulSoup
from contextlib import suppress
from dateutil import parser
from random import choice
from urllib.request import urlopen

SERVER_ID = 280439975911096320
TWITTER_CHANNEL_ID = 448716340816248832
SEIYUU_CHANNEL_ID = 309934970124763147
MUTED_ROLE_ID = 445572638543446016
BOT_ADMIN_ID = 299908261438816258
WUG_EVENTERNOTE_IDS = [6988, 3774, 6984, 6983, 6985, 6982, 6986, 6987]
WUG_MEMBERS = ['Wake Up, Girls', '吉岡茉祐', '永野愛理', '田中美海', '青山吉能', '山下七海', '奥野香耶', '高木美佑']
VIDEO_LINK_URLS = ['streamable.com', 'youtube.com']
WUG_OTHER_UNITS = ['Wake Up, Girls!', "Wake Up, May'n!", 'ハッカドール', 'D-selections', 'チーム“ハナヤマタ”', 'Zähre', '4U', 'Ci+LUS', 'Adhara', 'petit corolla', 'FIVE STARS', 'TEAM OHENRO。', 'フランシュシュ']
WUG_OSHI_NAMES = {
    'mayushii': ['mayushii', 'mayu', 'mayuchan', 'mayushi', 'mayuc'],
    'aichan': ['aichan', 'airi', 'chanai'],
    'minyami': ['minyami', 'minami', 'minachan', 'mina'],
    'yoppi': ['yoppi', 'yoshino', 'yopichan', 'yopi'],
    'nanamin': ['nanamin', 'nanami', 'nanachan', 'nana'],
    'kayatan': ['kayatan', 'kaya', 'kayachan'],
    'myu': ['myu', 'miyu', 'myuchan', 'myuu', 'myuuchan']
}
WUG_KAMIOSHI_ROLE_IDS = {
    'mayushii': 499826746904805377,
    'aichan': 499826827364139008,
    'minyami': 499826901939126273,
    'yoppi': 499826267890122753,
    'nanamin': 499826972235661322,
    'kayatan': 499826573231390730,
    'myu': 499827054586494976
}
WUG_ROLE_IDS = {
    'mayushii': 332788311280189443,
    'aichan': 333727530680844288,
    'minyami': 332793887200641028,
    'yoppi': 332796755399933953,
    'nanamin': 333721984196411392,
    'kayatan': 333721510164430848,
    'myu': 333722098377818115
}
WUG_ONMUSU_CHARS = {
    'mayushii': ['iizaka_mahiro', 0x98d98e],
    'aichan': ['matsushima_nazuki', 0x7ecfb3],
    'minyami': ['kurokawa_kira', 0xa09bdc],
    'yoppi': ['hitoyoshi_aoi', 0xfeeed6],
    'nanamin': ['kinosaki_arisa', 0xd7f498],
    'kayatan': ['unzen_inori', 0xe6e8ff],
    'myu': ['yumura_chiyo', 0xe25b54]
}
WUG_TWITTER_IDS = {
    'myu': 1112369342815956994,
    'mayushii': 1113758206436622336,
    'minyami': 1113445785004269568,
    'kayatan': 1123177804114190336,
    'yoppi': 1128244095887917056
}
WUG_INSTAGRAM_IDS = {
    'nanamin': 'aishite773',
    'kayatan': 'kaayaataaaan'
}
FAKE_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36', 
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0'
]

def parse_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['DEFAULT']

def get_wug_guild(guilds):
    return discord.utils.get(guilds, id=SERVER_ID)

def get_updates_channel(guilds):
    guild = discord.utils.get(guilds, id=SERVER_ID)
    return discord.utils.get(guild.channels, id=TWITTER_CHANNEL_ID)

def get_seiyuu_channel(guilds):
    guild = discord.utils.get(guilds, id=SERVER_ID)
    return discord.utils.get(guild.channels, id=SEIYUU_CHANNEL_ID)

def get_muted_role(guild):
    return discord.utils.get(guild.roles, id=MUTED_ROLE_ID)

def get_wug_role(guild, member):
    with suppress(Exception):
        return discord.utils.get(guild.roles, id=WUG_ROLE_IDS[parse_oshi_name(member)])

def get_oshi_colour(guild, member):
    with suppress(Exception):
        if member == 'Everyone':
            return discord.Colour.teal()
        return get_wug_role(guild, member).colour

def get_kamioshi_role(guild, member):
    with suppress(Exception):
        return discord.utils.get(guild.roles, id=WUG_KAMIOSHI_ROLE_IDS[parse_oshi_name(member)])

def dict_reverse(dictionary):
    return { v: k for k, v in dictionary.items() }

def parse_oshi_name(name):
    for oshi, names in WUG_OSHI_NAMES.items():
        if name.lower() in names:
            return oshi

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

def is_image_file(filename):
    return filename.endswith(('.jpg', '.png'))

def is_video_link(text):
    for url in VIDEO_LINK_URLS:
        if url in text:
            return True
    return False

def is_youtube_link(text):
    return text.find('googleads.g.doubleclick.net') == -1 and text.find('googleadservices.com') == -1 and not text.startswith(('/channel', '/user'))

def is_embeddable_content(content):
    return is_image_file(content) or is_video_link(content) or 'twitter.com' in content

def split_embeddable_content(tag_content):
    split_tag = tag_content.split()
    all_embeddable_content = True
    for line in split_tag:
        if is_embeddable_content(line):
            continue
        else:
            all_embeddable_content = False
    if all_embeddable_content:
        return split_tag
    split_tag = tag_content.splitlines()
    for line in split_tag:
        if is_embeddable_content(line):
            continue
        else:
            return
    return split_tag

def get_html_from_url(url):
    html_response = urlopen(url)
    return BeautifulSoup(html_response, 'html.parser')

def get_random_header():
    return { 'User-Agent': choice(FAKE_USER_AGENTS) }

def create_embed(author={}, title='', description='', colour=discord.Colour.light_grey(), url='', image='', thumbnail='', fields=[], footer={}, inline=False):
    embed = discord.Embed(title=title, description=description, colour=colour, url=url)
    if author:
        embed.set_author(name=author['name'], url=author.get('url', ''), icon_url=author.get('icon_url', ''))
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if footer:
        embed.set_footer(text=footer['text'], icon_url=footer.get('icon_url', ''))
    for field in fields:
        embed.add_field(name=field[0], value=field[1], inline=inline)
    return embed