import discord
import itertools
from discord.ext import commands
from redbot.core import Config
from redbot.core import checks
from redbot.core.bot import Red
from redbot.core.context import RedContext
from redbot.core.utils.chat_formatting import box, pagify
from collections import OrderedDict
from collections import Counter
import humanize

import argparse

import datetime as dt

from random import choice

DAYS = 2
LIMIT = 10000


def random_discord_color():
    """Return random color as an integer."""
    color = ''.join([choice('0123456789ABCDEF') for x in range(6)])
    color = int(color, 16)
    return discord.Color(value=color)

def grouper(n, iterable, fillvalue=None):
    """Helper function to split lists.

    Example:
    grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return (
        [e for e in t if e is not None]
        for t in itertools.zip_longest(*args))

class GuildLog:
    def __init__(self, guild, days=DAYS):
        self.guild = guild
        self.days = days

    def channel_embeds(self, log):

        em = discord.Embed(
            title=self.guild.name,
            description="Channel activity in the last {} days.".format(self.days),
            color=discord.Color.red()
        )
        em.set_thumbnail(url=self.guild.icon_url)
        embeds = [em]
        for log_groups in grouper(12, log):
            em = discord.Embed(
                title=self.guild.name,
                color=discord.Color.red()
            )
            for item in log_groups:
                name = "{}: {}".format(self.guild.get_channel(item['channel_id']).name, item['count'])
                value = ', '.join(['{}: {}'.format(author.display_name, count) for author, count in item['rank']])
                em.add_field(name=name, value=value)
            embeds.append(em)
        return embeds

class DStats:
    """Discord Statistics"""

    def __init__(self, bot: Red):
        """Init."""
        self.bot = bot
        self.config = Config.get_conf(self, identifier=209287691722817536, force_registration=True)
        default_global = {}
        default_guild = {}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.group()
    async def dstats(self, ctx: RedContext):
        """Discord stats."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @dstats.command(name="user")
    async def dstats_user(self, ctx: RedContext, member: discord.Member, limit=LIMIT, days=DAYS):
        """User stats."""
        log = OrderedDict()
        after = dt.datetime.utcnow() - dt.timedelta(days=days)

        async with ctx.typing():
            em = discord.Embed(
                title="{}#{}".format(member.name, member.discriminator),
                description="Channel activity in the last {} days.".format(days),
                color=member.color
            )
            em.set_thumbnail(url=member.avatar_url)

            last_seen = None
            for channel in ctx.guild.text_channels:
                async for message in channel.history(after=after, limit=limit, reverse=False):
                    if message.author == member:
                        channel = message.channel
                        if channel.id not in log:
                            log[channel.id] = 0
                        log[channel.id] += 1
                        if last_seen is None:
                            last_seen = message.created_at
                        last_seen = max(last_seen, message.created_at)

            em.add_field(
                name="Last seen",
                value="{}\n{}".format(
                    last_seen.strftime('%a, %b %d, %Y, %H:%M:%S UTC'),
                    humanize.naturaltime(dt.datetime.utcnow() - last_seen)
                )
            )

            log = OrderedDict(sorted(log.items(), key=lambda item: item[1], reverse=True))

            for channel_id, count in log.items():
                em.add_field(
                    name=ctx.guild.get_channel(channel_id).name,
                    value=count
                )

            await ctx.send(embed=em)

    @dstats.command(name="channels")
    @checks.mod_or_permissions()
    async def dstats_channels(self, ctx, limit=LIMIT, days=DAYS):
        """All users stats."""
        log = []
        after = dt.datetime.utcnow() - dt.timedelta(days=days)

        async with ctx.typing():
            # em = discord.Embed(
            #     title="{}".format(ctx.guild.name),
            #     description="Channel activity in the last {} days.".format(days),
            #     color=discord.Color.red()
            # )
            # em.set_thumbnail(url=ctx.guild.icon_url)
            for channel in ctx.guild.text_channels:
                authors = []
                async for message in channel.history(after=after, limit=limit, reverse=False):
                    authors.append(message.author)
                if len(authors) > 0:
                    log.append({
                        'channel_id': channel.id,
                        'rank': Counter(authors).most_common(),
                        'count': len(authors)
                    })
            log = sorted(log, key=lambda item: item['count'], reverse=True)

            # for channel_id, item in log.items():
            #     name = "{}: {}".format(ctx.guild.get_channel(channel_id).name, item['count'])
            #     value = ', '.join(['{}: {}'.format(author.display_name, count) for author, count in item['rank']])
            #     em.add_field(name=name, value=value)
            #
            # await ctx.send(embed=em)

            glog = GuildLog(ctx.guild, days=days)
            for em in glog.channel_embeds(log):
                await ctx.send(embed=em)








