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

    async def user_history_embed(self, member: discord.Member, days=2, limit=10000):
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        em = discord.Embed(
            title="{}#{}".format(member.name, member.discriminator),
            description="Channel activity in the last {} days.".format(days),
            color=member.color
        )
        em.set_thumbnail(url=member.avatar_url)

        last_seen = None
        skipped_channels = False
        history = OrderedDict()
        for channel in self.guild.text_channels:
            try:
                async for message in channel.history(after=after, limit=limit, reverse=False):
                    if message.author == member:
                        channel = message.channel
                        if channel.id not in history:
                            history[channel.id] = 0
                        history[channel.id] += 1
                        if last_seen is None:
                            last_seen = message.created_at
                        last_seen = max(last_seen, message.created_at)
            except discord.errors.Forbidden:
                skipped_channels = True
                pass

        em.add_field(
            name="Last seen",
            value="{}\n{}".format(
                last_seen.strftime('%a, %b %d, %Y, %H:%M:%S UTC'),
                humanize.naturaltime(dt.datetime.utcnow() - last_seen)
            ),
            inline=False
        )

        history = OrderedDict(sorted(history.items(), key=lambda item: item[1], reverse=True))

        for channel_id, count in history.items():
            em.add_field(
                name=self.guild.get_channel(channel_id).name,
                value=count
            )
        if skipped_channels:
            em.set_footer(text='May be incomplete: cannot access all channels.')
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
            except discord.errors.Forbidden:
                authors.append('No perms')
                history.append({
                    'channel_id': channel.id,
                    'rank': Counter(authors).most_common(),
                    'count': 0
                    })

        history = sorted(history, key=lambda item: item['count'], reverse=True)
        return history

    async def channel_history_embeds(self, days=2, limit=10000):
        """List of embeds with channel history."""
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

            no_perm_list = []
            for item in log_groups:
                try:
                    name = "{}: {}".format(self.guild.get_channel(item['channel_id']).name, item['count'])
                    value = ', '.join(['{}: {}'.format(author.display_name, count) for author, count in item['rank']])
                    em.add_field(name=name, value=value, inline=False)
                except AttributeError:
                    no_perm_channel = "{}".format(self.guild.get_channel(item['channel_id']).name)
                    no_perm_list.append(no_perm_channel)
            no_permissions = ', '.join(no_perm_list)
            if no_permissions:
                em.add_field(name=no_permissions, value='No permissions to read these channels.', inline=False)
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
    async def dstats_user(self, ctx: RedContext, member: discord.Member, limit=10000, days=7):
        """User stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            em = await glog.user_history_embed(member, days=days, limit=limit)
            await ctx.send(embed=em)

    @dstats.command(name="channels")
    @checks.mod_or_permissions()
    async def dstats_channels(self, ctx, limit=10000, days=2):
        """All users stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            embeds = await glog.channel_history_embeds(days, limit)
            for em in embeds:
                await ctx.send(embed=em)
