import asyncio
import hkdhelper as hkd

from calendar import month_name
from contextlib import suppress
from datetime import datetime
from dateutil import parser
from discord import Colour
from discord.ext import commands
from hkdhelper import create_embed, get_html_from_url, get_oshi_colour, parse_oshi_name
from pytz import timezone
from urllib.parse import quote

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def events(self, ctx, *, date: str=''):
        await ctx.channel.trigger_typing()
        event_urls = []
        current_time = datetime.now(timezone('Japan'))
        search_date = parser.parse(date) if date else current_time
        if current_time.month > search_date.month or current_time.month == search_date.month and current_time.day > search_date.day:
            search_year = current_time.year + 1
        else:
            search_year = current_time.year
        first = True
        for _ in range(3):
            with suppress(Exception):
                soup = get_html_from_url('https://www.eventernote.com/events/month/{0}-{1}-{2}/1?limit=1000'.format(search_year, search_date.month, search_date.day))
                result = soup.find_all(attrs={ 'class': ['date', 'event', 'actor', 'note_count'] })
                for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                    info = event[1].find_all('a')
                    event_time = event[1].find('span')
                    event_url = info[0]['href']
                    if event_url not in event_urls:
                        performers = [p.contents[0] for p in event[2].find_all('a')]
                        wug_performers = [p for p in performers if p in hkd.WUG_MEMBERS]
                        if not wug_performers:
                            continue
                        await ctx.channel.trigger_typing()
                        colour = get_oshi_colour(ctx.guild, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]) if len(wug_performers) == 1 else Colour.teal()
                        if first:
                            first = False
                            await ctx.send('**Events Involving WUG Members on {0:%Y}-{0:%m}-{0:%d} ({0:%A})**'.format(search_date.replace(year=search_year)))
                            await ctx.channel.trigger_typing()
                            await asyncio.sleep(0.5)
                        other_performers = [p for p in performers if p not in hkd.WUG_MEMBERS and p not in hkd.WUG_OTHER_UNITS]
                        embed_fields = []
                        embed_fields.append(('Location', info[1].contents[0]))
                        embed_fields.append(('Time', event_time.contents[0] if event_time else 'To be announced'))
                        embed_fields.append(('WUG Members', ', '.join(wug_performers)))
                        embed_fields.append(('Other Performers', ', '.join(other_performers) if other_performers else 'None'))
                        embed_fields.append(('Eventernote Attendees', event[3].find('p').contents[0]))
                        event_urls.append(event_url)
                        await asyncio.sleep(0.5)
                        await ctx.send(embed=create_embed(title=info[0].contents[0], colour=colour, url='https://www.eventernote.com{0}'.format(event_url), thumbnail=event[0].find('img')['src'], fields=embed_fields, inline=True))
                break
        if not event_urls:
            await ctx.send(embed=create_embed(description="Couldn't find any events on that day.", colour=Colour.red()))

    @commands.command()
    @commands.guild_only()
    async def eventsin(self, ctx, month: str, member: str=''):
        await ctx.channel.trigger_typing()
        search_month = hkd.parse_month(month)
        if search_month == 'None':
            await ctx.send(embed=create_embed(description="Couldn't find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.", colour=Colour.red()))
            return
        current_time = datetime.now(timezone('Japan'))
        search_year = str(current_time.year if current_time.month <= int(search_month) else current_time.year + 1)
        search_index = [0]
        wug_names = list(hkd.WUG_ROLE_IDS.keys())
        if member:
            if parse_oshi_name(member) not in wug_names:
                await ctx.send(embed=create_embed(description="Couldn't find any events. Please follow this format for searching for events: **!eventsin** April Mayushii.", colour=Colour.red()))
                return
            search_index = [wug_names.index(parse_oshi_name(member)) + 1]
        event_urls = []
        first = True
        search_start = False
        for i in search_index:
            for _ in range(3):
                with suppress(Exception):
                    soup = get_html_from_url('https://www.eventernote.com/actors/{0}/{1}/events?actor_id={1}&limit=5000'.format(quote(hkd.WUG_MEMBERS[i]), hkd.WUG_EVENTERNOTE_IDS[i]))
                    result = soup.find_all(attrs={ 'class': ['date', 'event', 'actor', 'note_count'] })
                    events = []
                    for event in [result[i:i + 4] for i in range(0, len(result), 4)]:
                        event_date = event[0].find('p').contents[0][:10]
                        if event_date[:4] == search_year and event_date[5:7] == search_month:
                            search_start = True
                            events.append(event)
                        elif search_start:
                            break
                        else:
                            continue
                    for event in reversed(events):
                        info = event[1].find_all('a')
                        event_date = event[0].find('p').contents[0][:10]
                        event_time = event[1].find('span')
                        event_url = info[0]['href']
                        if event_url not in event_urls:
                            performers = [p.contents[0] for p in event[2].find_all('a')]
                            wug_performers = [p for p in performers if p in hkd.WUG_MEMBERS]
                            if not wug_performers:
                                continue
                            await ctx.channel.trigger_typing()
                            colour = get_oshi_colour(ctx.guild, list(hkd.WUG_ROLE_IDS.keys())[hkd.WUG_MEMBERS.index(wug_performers[0]) - 1]) if len(wug_performers) == 1 else Colour.teal()
                            if first:
                                first = False
                                await ctx.send('**Events for {0} in {1} {2}**'.format(member.title() if member else 'Wake Up, Girls!', month_name[int(search_month)], search_year))
                                await asyncio.sleep(0.5)
                            other_performers = [p for p in performers if p not in hkd.WUG_MEMBERS and p not in hkd.WUG_OTHER_UNITS]
                            embed_fields = []
                            embed_fields.append(('Location', info[1].contents[0]))
                            embed_fields.append(('Date', '{0} ({1:%A})'.format(event_date, parser.parse(event_date))))
                            embed_fields.append(('Time', event_time.contents[0] if event_time else 'To be announced'))
                            embed_fields.append(('WUG Members', ', '.join(wug_performers)))
                            embed_fields.append(('Other Performers', ', '.join(other_performers) if other_performers else 'None'))
                            embed_fields.append(('Eventernote Attendees', event[3].find('p').contents[0]))
                            event_urls.append(event_url)
                            await asyncio.sleep(0.5)
                            await ctx.send(embed=create_embed(title=info[0].contents[0], colour=colour, url='https://www.eventernote.com{0}'.format(event_url), thumbnail=event[0].find('img')['src'], fields=embed_fields, inline=True))
                    break
        if not event_urls:
            await ctx.send(embed=create_embed(description="Couldn't find any events during that month.", colour=Colour.red()))