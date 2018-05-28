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

import logging
import argparse

import datetime as dt

from random import choice

logger = logging.getLogger(__name__)


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
    def __init__(self, guild):
        self.guild = guild

    async def user_history(self, guild: discord.Guild, member: discord.Member, days=2, limit=10000):
        """User history in a guild."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        history = []
        last_seen = None
        for channel in guild.text_channels:
            try:
                async for message in channel.history(after=after, limit=limit, reverse=False):
                    if message.author == member:
                        history.append(channel.id)
                    if last_seen is None:
                        last_seen = message.created_at
                    last_seen = max(last_seen, message.created_at)
            except discord.errors.Forbidden as e:
                logger.exception("No permission for {}: {}".format(channel.name, channel.id))

        return last_seen, Counter(history).most_common()

    async def user_history_2(self, guild: discord.Guild, member: discord.Member, days=2, limit=10000):
        """User history in a guild."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        last_seen = None
        history = OrderedDict()
        for channel in guild.text_channels:
            try:
                async for message in channel.history(after=after, limit=limit, reverse=False):
                    if message.author == member:
                        if channel.id not in history:
                            history[channel.id] = 0
                        history[channel.id] += 1
                        if last_seen is None:
                            last_seen = message.created_at
                        last_seen = max(last_seen, message.created_at)
            except discord.errors.Forbidden as e:
                logger.exception("No permission for {}: {}".format(channel.name, channel.id))
        return last_seen, OrderedDict(sorted(history.items(), key=lambda item: item[1], reverse=True))

    async def user_history_embed(self, member: discord.Member, days=2, limit=10000):
        last_seen, history = await self.user_history_2(self.guild, member, days, limit)

        em = discord.Embed(
            title="{}#{}".format(member.name, member.discriminator),
            description="Channel activity in the last {} days.".format(days),
            color=member.color
        )
        em.set_thumbnail(url=member.avatar_url)
        em.add_field(
            name="Last seen",
            value="{}\n{}".format(
                last_seen.strftime('%a, %b %d, %Y, %H:%M:%S UTC'),
                humanize.naturaltime(dt.datetime.utcnow() - last_seen)
            ),
            inline=False
        )

        if isinstance(history, dict):
            items = history.items()
        else:
            items = history

        for channel_id, count in items:
            em.add_field(
                name=self.guild.get_channel(channel_id).name,
                value=count
            )

        return em

    async def channel_history(self, after=None, limit=10000):
        history = []
        for channel in self.guild.text_channels:
            authors = []
            try:
                async for message in channel.history(after=after, limit=limit, reverse=False):
                    authors.append(message.author)
                if len(authors) > 0:
                    history.append({
                        'channel_id': channel.id,
                        'rank': Counter(authors).most_common(),
                        'count': len(authors)
                    })
            except Exception as e:
                logger.exception(e)
        history = sorted(history, key=lambda item: item['count'], reverse=True)
        return history

    async def channels_history_embeds(self, days=2, limit=10000):
        """List of embeds with all channel history."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        history = await self.channel_history(after=after, limit=limit)

        em = discord.Embed(
            title=self.guild.name,
            description="Channel activity in the last {} days.".format(days),
            color=discord.Color.red()
        )
        em.set_thumbnail(url=self.guild.icon_url)
        embeds = [em]
        for log_groups in grouper(12, history):
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

    async def channel_history_embeds(self, channel: discord.TextChannel, days=2, limit=10000):
        """List of embeds with one channel history."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)

        history = []
        authors = []
        try:
            async for message in channel.history(after=after, limit=limit, reverse=False):
                authors.append(message.author)
            if len(authors) > 0:
                history.append({
                    'channel_id': channel.id,
                    'rank': Counter(authors).most_common(),
                    'count': len(authors)
                })
        except Exception as e:
            logger.exception(e)

        history = sorted(history, key=lambda item: item['count'], reverse=True)

        em = discord.Embed(
            title=self.guild.name,
            description="Channel activity in the last {} days.".format(days),
            color=discord.Color.red()
        )
        em.set_thumbnail(url=self.guild.icon_url)
        embeds = [em]
        for log_groups in grouper(12, history):
            em = discord.Embed(
                title=self.guild.name,
                color=discord.Color.red()
            )
            for item in log_groups:
                name = "{}: {}".format(self.guild.get_channel(item['channel_id']).name, item['count'])
                value = ', '.join(['{}: {}'.format(author.display_name, count) for author, count in item['rank']])
                if len(value) > 1024:
                    value = value[:1024]
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
    @checks.mod_or_permissions()
    async def dstats_user(self, ctx: RedContext, member: discord.Member, limit=10000, days=7):
        """User stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            em = await glog.user_history_embed(member, days=days, limit=limit)
            await ctx.send(embed=em)

    @dstats.command(name="channel")
    @checks.mod_or_permissions()
    async def dstats_channel(self, ctx, channel: discord.TextChannel, limit=10000, days=7):
        """All users stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            embeds = await glog.channel_history_embeds(channel, days=days, limit=limit)
            for em in embeds:
                await ctx.send(embed=em)

    @dstats.command(name="channels")
    @checks.mod_or_permissions()
    async def dstats_channels(self, ctx:RedContext, limit=10000, days=2):
        """All users stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            embeds = await glog.channels_history_embeds(days, limit)
            for em in embeds:
                await ctx.send(embed=em)








