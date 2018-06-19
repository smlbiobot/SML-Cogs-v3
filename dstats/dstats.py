import argparse
import datetime as dt
import itertools
import logging
from collections import Counter
from collections import OrderedDict
from random import choice

import discord
import humanize
from discord.ext import commands
from redbot.core import Config
from redbot.core import checks
from redbot.core.bot import Red
# from redbot.core.context import RedContext
from redbot.core.commands import Context

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


def parser(cat):
    """Argument parser."""
    parser = argparse.ArgumentParser(prog='[p]dstats')
    parser.add_argument(
        '-r', '--roles',
        nargs='+',
        help='Include roles')
    parser.add_argument(
        '-t', '--top',
        nargs=1,
        help='Top N results',
        type=int,
        default=10
    )
    parser.add_argument(
        '-d', '--days',
        help='Last N days',
        type=int,
        default=7
    )
    parser.add_argument(
        '-l', '--limit',
        help='Limit N messages',
        type=int,
        default=10000
    )
    return parser


def get_guild_roles(guild: discord.Guild, names):
    """Given a list of role names, get list of guild Role objects."""
    if not names:
        return []
    o = []
    lower_names = [n.lower() for n in names]
    for r in guild.roles:
        if r.name.lower() in lower_names:
            o.append(r)
    return o


class GuildLog:
    def __init__(self, guild):
        self.guild = guild

    async def user_history(self, guild: discord.Guild, member: discord.Member, days=2, limit=10000):
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
        last_seen, history = await self.user_history(self.guild, member, days, limit)

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

    def get_channel_history_embeds(self, group_by=4, history=None, days=None):
        """List of embeds"""
        embeds = []
        for log_groups in grouper(group_by, history):
            em = discord.Embed(
                title=self.guild.name,
                description="Channel activity in the last {} days.".format(days),
                color=discord.Color.red()
            )
            em.set_footer(text=self.guild.name, icon_url=self.guild.icon_url)
            for item in log_groups:
                name = "{}: {}".format(self.guild.get_channel(item['channel_id']).name, item['count'])
                value = ', '.join(['{}: {}'.format(author.display_name, count) for author, count in item['rank']])
                if len(value) > 1000:
                    value = value[:1000]
                em.add_field(name=name, value=value)
            embeds.append(em)
        return embeds

    async def channels_history_embeds(self, days=2, limit=10000):
        """List of embeds with all channel history."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        history = await self.channel_history(after=after, limit=limit)

        return self.get_channel_history_embeds(history=history, days=days)

    async def channel_history_embeds(self, channel: discord.TextChannel, limit=10000, days=7, roles=None):
        """List of embeds with one channel history."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)

        history = []
        authors = []

        if roles is None:
            roles = []

        try:
            async for message in channel.history(after=after, limit=limit, reverse=False):
                if getattr(message.author, 'roles', False):
                    if len(roles) == 0 or any([author_role in roles for author_role in message.author.roles]):
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

        return self.get_channel_history_embeds(history=history, days=days)


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
    async def dstats(self, ctx: Context):
        """Discord stats."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @dstats.command(name="user")
    @checks.mod_or_permissions()
    async def dstats_user(self, ctx: Context, member: discord.Member, limit=10000, days=7):
        """User stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            em = await glog.user_history_embed(member, days=days, limit=limit)
            await ctx.send(embed=em)

    @dstats.command(name="channel")
    @checks.mod_or_permissions()
    async def dstats_channel(self, ctx, channel: discord.TextChannel, *args):
        """Channel stats.

        usage: [p]dstats [-h] [-r ROLES [ROLES ...]] [-t TOP] [-d DAYS] [-l LIMIT]

        optional arguments:
          -h, --help            show this help message and exit
          -r ROLES [ROLES ...], --roles ROLES [ROLES ...]
                                    Include roles
          -t TOP, --top TOP         Top N results
          -d DAYS, --days DAYS      Last N days
          -l LIMIT, --limit LIMIT   Limit N messages
        """
        p = parser('channel')
        try:
            pargs = p.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return

        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            days = pargs.days
            limit = pargs.limit
            roles = get_guild_roles(ctx.guild, pargs.roles)
            embeds = await glog.channel_history_embeds(channel, days=days, limit=limit, roles=roles)
            for em in embeds:
                await ctx.send(embed=em)

    @dstats.command(name="channels")
    @checks.mod_or_permissions()
    async def dstats_channels(self, ctx: Context):
        """All users stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            embeds = await glog.channels_history_embeds()
            for em in embeds:
                await ctx.send(embed=em)
