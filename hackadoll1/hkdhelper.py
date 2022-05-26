import asyncio
import json
import os
import re
from contextlib import suppress
from itertools import takewhile
from random import choice
from urllib.parse import urlparse
from urllib.request import urlopen

import configparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser
from discord import Colour, Embed, File, utils as disc_utils
from discord_slash.utils.manage_commands import create_choice
from lxml.html import fromstring
from config import CONFIG

TWITTER_CHANNEL_ID = 448716340816248832
SEIYUU_CHANNEL_ID = 309934970124763147
WELCOME_CHANNEL_ID = 361552652988973077
MUTED_ROLE_ID = 445572638543446016
BOT_ADMIN_ID = 299908261438816258
ADMIN_ID = 309964848580526081
WUG_EVENTERNOTE_IDS = [6988, 3774, 6984, 6983, 6985, 6982, 6986, 6987]
WUG_MEMBERS = ['Wake Up, Girls', '吉岡茉祐', '永野愛理', '田中美海', '青山吉能', '山下七海', '奥野香耶', '高木美佑']
VIDEO_LINK_URLS = ['streamable.com', 'youtube.com']
WUG_OTHER_UNITS = ['Wake Up, Girls!', "Wake Up, May'n!", 'ハッカドール', 'D-selections', 'チーム“ハナヤマタ”', 'Zähre', '4U', 'Ci+LUS', 'Adhara', 'petit corolla', 'FIVE STARS', 'TEAM OHENRO。', 'フランシュシュ', '8/pLanet!!', 'B.A.C', 'Peaky P-key', 'Clutch!', 'KOKORi', 'ノンシュガー', 'ときめきアイドル project']
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
    'yoppi': 1128244095887917056,
    'aichan': 1134589498610802688
}
WUG_INSTAGRAM_IDS = {
    'nanamin': 'aishite773',
    'kayatan': '_kayarea_',
    'minyami': 'minazou_in_sta',
    'yoppi': 'yopipinsta555',
    'mayushii': 'yoshioka_mayuc',
    'myu': 'miyu_takagi'
}
WUG_YOUTUBE_CHANNELS = {
    'nanamin': 'UCZU_aYCkJToNj5OyN1S1BdQ',
    'myu': 'UCcRVUN5NDN6U6nKmWJm4-yA',
    'yoppi': 'UCCIUO6dSL13XdiZlJGn3xYA',
    'aichan': 'UCvpjMblxDRU3DPXH1CMRtqw'
}
WUG_SHOWROOM_IDS = {
    'aichan': 316587
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
BANNED_USER_PATTERNS = [
    'twitter.com/h0nde',
    'Love Live! Sunshine!!'
]

def parse_config():
    config_parser = configparser.ConfigParser()
    config_parser.read('config.ini')
    return config_parser['DEFAULT']

def get_wug_server_id():
    return CONFIG.SERVER_ID

def get_all_guild_ids():
    return [CONFIG.SERVER_ID, CONFIG.TEST_SERVER_ID]

def get_wug_guild(guilds):
    return disc_utils.get(guilds, id=CONFIG.SERVER_ID)

def get_updates_channel(guilds):
    guild = disc_utils.get(guilds, id=CONFIG.SERVER_ID)
    return disc_utils.get(guild.channels, id=TWITTER_CHANNEL_ID)

def get_seiyuu_channel(guilds):
    guild = disc_utils.get(guilds, id=CONFIG.SERVER_ID)
    return disc_utils.get(guild.channels, id=SEIYUU_CHANNEL_ID)

def get_muted_role(guild):
    return disc_utils.get(guild.roles, id=MUTED_ROLE_ID)

def get_wug_role(guild, member):
    with suppress(Exception):
        return disc_utils.get(guild.roles, id=WUG_ROLE_IDS[parse_oshi_name(member)])

def get_oshi_colour(guild, member):
    with suppress(Exception):
        if member == 'Everyone':
            return Colour.teal()
        return get_wug_role(guild, member).colour

def get_kamioshi_role(guild, member):
    with suppress(Exception):
        return disc_utils.get(guild.roles, id=WUG_KAMIOSHI_ROLE_IDS[parse_oshi_name(member)])

def dict_reverse(dictionary):
    return {v: k for k, v in dictionary.items()}

def parse_oshi_name(name):
    for oshi, names in WUG_OSHI_NAMES.items():
        if name.lower() in names:
            return oshi
    return name

def get_member_choices():
    choices = []
    for member in WUG_OSHI_NAMES:
        choices.append(create_choice(name=member.title(), value=member))
    return choices

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

def get_id_from_url(url, search, end):
    if search not in url:
        return None
    search_index = url.find(search)
    start = url[search_index + len(search):]
    end_index = start.find(end)
    return start[:end_index] if end_index != -1 else start

def is_blog_post(expanded_url):
    return 'ameblo.jp/eino-airi' in expanded_url

def is_image_file(filename):
    return filename.endswith(('.jpg', '.png'))

def is_video_link(text):
    for url in VIDEO_LINK_URLS:
        if url in text:
            return True
    return False

def is_embeddable_content(content):
    return is_image_file(content) or is_video_link(content) or check_url_host(content, ['twitter.com'])

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
            return []
    return split_tag

def get_html_from_url(url):
    html_response = urlopen(url)
    return BeautifulSoup(html_response, 'html.parser')

def get_tweet_id_from_url(tweet_url):
    return ''.join(takewhile(lambda x: x.isdigit(), iter(tweet_url.split('/status/')[-1])))

def get_media_from_blog_post(blog_url):
    for _ in range(3):
        for article_class in ['skin-entryBody', 'articleText']:
            with suppress(Exception):
                soup = get_html_from_url(blog_url)
                blog_entry = soup.find_all(attrs={'class': article_class}, limit=1)[0]
                return [p['href'] for p in blog_entry.find_all('a') if is_image_file(p['href'])], [v['src'].split('.jp/?v=', 1)[1] for v in soup.find_all('iframe') if 'blog-video' in v['src']]
    return [], []

def get_ids_from_ytdl_result(result):
    vid_ids = []
    if (entries := result.get('entries', [])):
        for entry in entries:
            vid_ids.append(entry.get('id', ''))
    else:
        vid_ids.append(result.get('id'))
    return vid_ids

def get_video_data_from_youtube(channel_id):
    with suppress(Exception):
        response = requests.get('https://www.youtube.com/channel/{0}/videos?view=2&live_view=501'.format(channel_id), headers=get_random_header())
        if yt_data_script := re.search(r'var ytInitialData\s*=\s*(.*);</script>', response.text, re.MULTILINE):
            yt_data = json.loads(yt_data_script.group(1))
            tabs = yt_data['contents']['twoColumnBrowseResultsRenderer']['tabs']
            if videos_tab := [t for t in tabs if t.get('tabRenderer') and t['tabRenderer']['title'] == 'Videos']:
                tab_contents = videos_tab[0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]
                if 'shelfRenderer' in tab_contents:
                    return tab_contents['shelfRenderer']['content']['gridRenderer']['items']
                return tab_contents['gridRenderer']['items']
    return []

def check_url_host(url, allow_list):
    if not (host := urlparse(url).hostname):
        return False
    return any([host.endswith(allowed_url) for allowed_url in allow_list])

def get_random_header():
    return {'User-Agent': choice(FAKE_USER_AGENTS)}

def get_random_proxy():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:20]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return choice(tuple(proxies))

def create_embed(author={}, title='', description='', colour=Colour(0x242424), url='', image='', thumbnail='', fields=[], footer={}, inline=False):
    if len(description) > 2048:
        description = description[:2044] + ' ...'
    embed = Embed(title=title, description=description, colour=colour, url=url)
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

async def send_content_with_delay(ctx, content):
    for item in content:
        await asyncio.sleep(0.5)
        await ctx.send(item)

async def send_video_check_filesize(ctx, video_file, video_link):
    if os.path.getsize(video_file) < ctx.guild.filesize_limit:
        await ctx.send(file=File(video_file))
    else:
        await ctx.send(video_link)
    with suppress(Exception):
        os.remove(video_file)
