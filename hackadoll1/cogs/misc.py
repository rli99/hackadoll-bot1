import asyncio
import os
import subprocess
import time
from contextlib import suppress
from datetime import datetime
from decimal import Decimal
from random import randrange
from urllib.parse import quote

import requests
import pytz
import youtube_dl
import hkdhelper as hkd
from discord import Colour, File
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option
from forex_python.converter import CurrencyRates
from googletrans import Translator
from pycountry import countries
from timezonefinder import TimezoneFinder

class Misc(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    @cog_ext.cog_slash(
        description="Translate the provided Japanese text into English via Google Translate.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="text",
                description="The text to translate.",
                option_type=3,
                required=True
            )
        ]
    )
    async def translate(self, ctx, *, text: str):
        await ctx.defer()
        await ctx.send(embed=hkd.create_embed(description=Translator().translate(text, src='ja', dest='en').text))

    @cog_ext.cog_slash(
        description="Convert currency from one type to another.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="conversion",
                description="Convert amount of currency-a to currency-b.",
                option_type=3,
                required=True
            )
        ]
    )
    async def currency(self, ctx, *conversion: str):
        await ctx.defer()
        if len(conversion) == 4 and conversion[2].lower() == 'to':
            with suppress(Exception):
                result = CurrencyRates().convert(conversion[1].upper(), conversion[3].upper(), Decimal(conversion[0]))
                await ctx.send(embed=hkd.create_embed(title='{0} {1}'.format('{:f}'.format(result).rstrip('0').rstrip('.'), conversion[3].upper())))
                return
        await ctx.send(embed=hkd.create_embed(description="Couldn't convert. Please follow this format for converting currency: **/currency** 12.34 AUD to USD.", colour=Colour.red()))

    @cog_ext.cog_slash(
        description="Show weather information for the specified location.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="location",
                description="The location to show the weather for.",
                option_type=3,
                required=True
            )
        ]
    )
    async def weather(self, ctx, *, location: str):
        await ctx.defer()
        if len(query := location.split(',')) > 1:
            with suppress(Exception):
                query[1] = countries.get(name=query[1].strip().title()).alpha_2
        with suppress(Exception):
            result = requests.get('http://api.openweathermap.org/data/2.5/weather', params={'q': ','.join(query), 'APPID': self.config['weather_api_key']}).json()
            timezone = pytz.timezone(TimezoneFinder().timezone_at(lat=result['coord']['lat'], lng=result['coord']['lon']))
            embed_fields = []
            embed_fields.append(('Weather', '{0}'.format(result['weather'][0]['description'].title())))
            embed_fields.append(('Temperature', '{0} °C, {1} °F'.format('{0:.2f}'.format(float(result['main']['temp']) - 273.15), '{0:.2f}'.format((1.8 * (float(result['main']['temp']) - 273.15)) + 32.0))))
            embed_fields.append(('Humidity', '{0}%'.format(result['main']['humidity'])))
            embed_fields.append(('Wind Speed', '{0} m/s'.format(result['wind']['speed'])))
            embed_fields.append(('Sunrise', '{0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunrise'], tz=timezone))))
            embed_fields.append(('Sunset', '{0:%I}:{0:%M} {0:%p}'.format(datetime.fromtimestamp(result['sys']['sunset'], tz=timezone))))
            embed_fields.append(('Pressure', '{0} hPa'.format(result['main']['pressure'])))
            await ctx.send(content='**Weather for {0}, {1}**'.format(result['name'], countries.lookup(result['sys']['country']).name), embed=hkd.create_embed(fields=embed_fields, inline=True))
            return
        await ctx.send(embed=hkd.create_embed(description="Couldn't get weather. Please follow this format for checking the weather: **/weather** Melbourne, Australia.", colour=Colour.red()))

    @cog_ext.cog_slash(
        description="Randomly choose from one of the provided options.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="options",
                description="The options to choose from.",
                option_type=3,
                required=True
            )
        ]
    )
    async def choose(self, ctx, *options: str):
        await ctx.defer()
        if len(options) > 1:
            await ctx.send(embed=hkd.create_embed(description=options[randrange(len(options))]))
        else:
            await ctx.send(embed=hkd.create_embed(description='Please provide 2 or more options to choose from, e.g. **/choose** *option1* *option2*.', colour=Colour.red()))

    @cog_ext.cog_slash(
        description="Gets the top result from YouTube based on the provided search terms.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="query",
                description="Terms to search for on YouTube.",
                option_type=3,
                required=True
            )
        ]
    )
    async def youtube(self, ctx, *, query: str):
        await ctx.defer()
        for _ in range(3):
            with suppress(Exception):
                soup = hkd.get_html_from_url('https://www.youtube.com/results?search_query={0}'.format(quote(query)))
                for result in soup.find_all(attrs={'class': 'yt-uix-tile-link'}):
                    link = result['href']
                    if hkd.is_youtube_link(link):
                        await ctx.send('https://www.youtube.com{0}'.format(link))
                        return
                break
        await ctx.send(embed=hkd.create_embed(title="Couldn't find any results.", colour=Colour.red()))

    @cog_ext.cog_slash(
        name="dl-vid",
        description="Attempt to download the video from the specified URL using youtube-dl.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="url",
                description="URL to try and download video from.",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.guild_only()
    async def dl_vid(self, ctx, url: str):
        await ctx.defer()
        await ctx.send('Attempting to download the video using youtube-dl. Please wait.')
        result = {}
        with suppress(Exception):
            ytdl_opts = {'outtmpl': '%(id)s.%(ext)s'}
            with youtube_dl.YoutubeDL(ytdl_opts) as ytdl:
                result = ytdl.extract_info(url)
        if not (vid_ids := hkd.get_ids_from_ytdl_result(result)):
            await ctx.send(embed=hkd.create_embed(title='Failed to download video.', colour=Colour.red()))
            return
        if not (files := [f for f in os.listdir('.') if os.path.isfile(f) and f.startswith(vid_ids[0])]):
            for _ in range(3):
                with suppress(Exception):
                    ytdl_opts = {'outtmpl': '%(id)s.%(ext)s', 'proxy': hkd.get_random_proxy()}
                    with youtube_dl.YoutubeDL(ytdl_opts) as ytdl:
                        result = ytdl.extract_info(url)
                        break
        if not (files := [f for f in os.listdir('.') if os.path.isfile(f) and f.startswith(vid_ids[0])]):
            await ctx.send(embed=hkd.create_embed(title='Failed to download video.', colour=Colour.red()))
            return        
        for vid_id in vid_ids:
            if (files := [f for f in os.listdir('.') if os.path.isfile(f) and f.startswith(vid_id)]):
                vid_filename = files[0]
                if os.path.getsize(vid_filename) < ctx.guild.filesize_limit:
                    await ctx.send(file=File(vid_filename))
                    with suppress(Exception):
                        os.remove(vid_filename)
                else:
                    await ctx.send('Download complete. Now uploading video to Google Drive. Please wait.')
                    proc = subprocess.Popen(args=['python', 'gdrive_upload.py', vid_filename, self.config['uploads_folder']])
                    while proc.poll() is None:
                        await asyncio.sleep(1)
                    if proc.returncode != 0:
                        await ctx.send(embed=hkd.create_embed(title='Failed to upload video to Google Drive.', colour=Colour.red()))
                        with suppress(Exception):
                            os.remove(vid_filename)
                        return
                    await ctx.send(content='{0.mention}'.format(ctx.author), embed=hkd.create_embed(description='Upload complete. Your video is available here: https://drive.google.com/open?id={0}. The Google Drive folder has limited space so it will be purged from time to time.'.format(self.config['uploads_folder'])))

    @cog_ext.cog_slash(
        description="Show the Onsen Musume profile for the character of the specified member.",
        guild_ids=hkd.get_all_guild_ids(),
        options=[
            create_option(
                name="member",
                description="The member that you want to see the Onmusu profile for.",
                option_type=3,
                required=True,
                choices=hkd.get_member_choices()
            )
        ]
    )
    async def onmusu(self, ctx, member: str = ''):
        await ctx.defer()
        char, char_colour = hkd.WUG_ONMUSU_CHARS[hkd.parse_oshi_name(member)]
        profile_link = 'https://onsen-musume.jp/character/{0}'.format(char)
        soup = hkd.get_html_from_url(profile_link)
        char_pic = 'https://onsen-musume.jp{0}'.format(soup.find('div', class_='character_ph__main').find('img')['src'])
        serifu = soup.find('div', class_='character_ph__serif').find('img')['alt']
        char_main = soup.find('div', class_='character_post__main')
        char_name = char_main.find('img')['alt']
        seiyuu = char_main.find('h2').find('img')['alt'][3:7]
        char_catch = char_main.find('p', class_='character_post__catch').contents[0]
        embed_fields = []
        for item in char_main.find('ul', class_='character_profile').find_all('li'):
            for i, entry in enumerate(item.find_all('span')):
                embed_fields.append((entry.contents[0], item.contents[(i + 1) * 2][1:]))
        soup = hkd.get_html_from_url('https://onsen-musume.jp/character/')
        thumbnail = 'https://onsen-musume.jp{0}'.format(soup.find('li', class_='character-list__item02 {0}'.format(char)).find('img')['src'])
        author = {}
        author['name'] = char_name
        author['url'] = profile_link
        author['icon_url'] = 'https://onsen-musume.jp/wp/wp-content/themes/onsenmusume/pc/assets/img/character/thumb/list/yu_icon.png'
        footer = {}
        footer['text'] = serifu
        await ctx.send(embed=hkd.create_embed(author=author, title='CV: {0}'.format(seiyuu), description=char_catch, colour=Colour(char_colour), image=char_pic, thumbnail=thumbnail, fields=embed_fields, footer=footer, inline=True))
