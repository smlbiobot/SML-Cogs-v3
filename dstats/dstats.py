import argparse
import datetime as dt
import itertools
import logging
import re
from collections import Counter
from collections import OrderedDict
from random import choice

import discord
import humanize
from redbot.core import Config
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context

from .stopwords import stop_words
from .utils import get_emoji

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


def parser():
    """Argument parser."""
    parser = argparse.ArgumentParser(prog='[p]dstats')
    parser.add_argument(
        '-r', '--roles',
        nargs='+',
        help='Include roles')
    parser.add_argument(
        '-n', '--top',
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
    parser.add_argument(
        '-t', '--text',
        help='Text match',
        type=str,
        default=''
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
                async for message in channel.history(after=after, limit=limit, oldest_first=False):
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

        value = "None"
        if last_seen:
            value = "{}\n{}".format(
                last_seen.strftime('%a, %b %d, %Y, %H:%M:%S UTC'),
                humanize.naturaltime(dt.datetime.utcnow() - last_seen)
            )
        em.add_field(
            name="Last seen",
            value=value,
            inline=False
        )

        if isinstance(history, dict):
            items = history.items()
        else:
            items = history

        # total count
        total_count = sum([count for channel_id, count in items])
        em.add_field(name="Total messages", value=total_count)

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
                async for message in channel.history(after=after, limit=limit, oldest_first=False):
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

    def get_channel_history_embeds(self, group_by=4, history=None, days=None, text=None, author_count=0,
                                   message_count=0, author_char_count_list=None, enable_char_count=False):
        """List of embeds"""
        embeds = []
        for log_groups in grouper(group_by, history):
            desc = f"Channel activity for in the last {days} day(s)"
            if text is not None and len(text) > 0:
                desc += ", containing `{}` ".format(text)
            em = discord.Embed(
                title=self.guild.name,
                description=desc,
                color=discord.Color.red()
            )
            em.add_field(name="Author count", value=f"{author_count}")
            em.add_field(name="Message count", value=f"{message_count}")
            em.set_footer(text=self.guild.name, icon_url=self.guild.icon_url)
            for item in log_groups:
                name = "{}: {}".format(self.guild.get_channel(item['channel_id']).name, item['count'])
                value = ' - '.join(['{} {}'.format(author.display_name, count) for author, count in item['rank']])
                if len(value) > 1000:
                    value = value[:1000]
                em.add_field(name=name, value=value, inline=False)
            embeds.append(em)

            # add author by author_char_count
            if enable_char_count:
                if author_char_count_list:
                    value = ' - '.join([f"{item['name']} {item['count']}" for item in author_char_count_list])
                    if len(value) > 1000:
                        value = value[:1000]
                    em.add_field(name="Character count", value=value, inline=False)

        return embeds

    async def channel_history_embeds(
            self,
            channel: discord.TextChannel,
            limit=10000,
            days=7,
            roles=None,
            text=None,
            enable_char_count=False,
    ):
        """List of embeds with one channel history."""
        after = dt.datetime.utcnow() - dt.timedelta(days=days)

        history = []
        authors = []
        author_ids = set()
        message_count = 0
        character_count = 0
        author_char_count = dict()

        if roles is None:
            roles = []

        try:
            async for message in channel.history(after=after, limit=limit):
                add_it = False
                if text is not None and text not in message.content:
                    # add_it = False
                    continue

                # if not getattr(message.author, 'roles', False):
                #     continue

                if len(roles) == 0 or any([author_role in roles for author_role in message.author.roles]):
                    add_it = True

                if not add_it:
                    continue

                authors.append(message.author)
                author_ids.add(message.author.id)
                message_count += 1

                if enable_char_count:
                    character_count = len(message.content)
                    if message.author.id not in author_char_count:
                        author_char_count[message.author.id] = 0
                    author_char_count[message.author.id] += character_count

            if len(authors) > 0:
                history.append({
                    'channel_id': channel.id,
                    'rank': Counter(authors).most_common(),
                    'count': len(authors),
                })
        except Exception as e:
            logger.exception(e)

        history = sorted(history, key=lambda item: item['count'], reverse=True)

        author_char_count_list = []
        for k, v in author_char_count.items():
            uid = k
            member = channel.guild.get_member(k)
            if member:
                name = member.display_name
            else:
                name = uid
            count = v
            author_char_count_list.append(dict(
                id=uid,
                name=name,
                count=count
            ))

        author_char_count_list.sort(key=lambda item: item['count'], reverse=True)

        return self.get_channel_history_embeds(
            history=history,
            days=days,
            text=text,
            author_count=len(author_ids),
            message_count=message_count,
            author_char_count_list=author_char_count_list,
            enable_char_count=enable_char_count,
        )

    async def server_history(self, limit=10000, days=7, roles=None, text=None):
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        authors = dict()
        channels = dict()
        try:
            for channel in self.guild.text_channels:
                async for message in channel.history(after=after, limit=limit, oldest_first=False):
                    author = message.author
                    if author.id not in authors:
                        authors[author.id] = 0
                    authors[author.id] += 1

                    if channel.id not in channels:
                        channels[channel.id] = 0
                    channels[channel.id] += 1

        except Exception as e:
            logger.exception(e)

        return dict(authors=authors, channels=channels)

    async def users_history(self, limit=10000, days=7, roles=None, text=None):
        after = dt.datetime.utcnow() - dt.timedelta(days=days)
        authors = dict()
        try:
            for channel in self.guild.text_channels:
                async for message in channel.history(after=after, limit=limit, oldest_first=False):
                    if text is not None:
                        if text.lower() not in message.content.lower():
                            continue
                    author = message.author
                    if author.id not in authors:
                        authors[author.id] = 0
                    authors[author.id] += 1

        except Exception as e:
            logger.exception(e)

        items = []
        for author_id, count in authors.items():
            items.append(dict(
                author_id=author_id,
                count=count
            ))

        items = sorted(items, key=lambda x: x.get('count', 0), reverse=True)

        for index, item in enumerate(items):
            item['rank'] = index + 1

        return items


class DStats(commands.Cog):
    """Discord Statistics"""

    def __init__(self, bot: Red):
        """Init."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=209287691722817536, force_registration=True)
        default_global = {}
        default_guild = {}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.group()
    async def dstats(self, ctx: Context):
        """Discord stats."""
        pass

    @dstats.command(name="user")
    @checks.mod_or_permissions()
    async def dstats_user(self, ctx: Context, member: discord.Member, limit=10000, days=7):
        """User stats."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            em = await glog.user_history_embed(member, days=days, limit=limit)
            await ctx.send(embed=em)

    @dstats.command(name="mentions")
    @checks.mod_or_permissions()
    async def dstats_mentions(self, ctx: Context, limit=10000):
        """Count mentions by users"""
        guild = ctx.guild
        mentioned = dict()
        ch = ctx.message.channel

        async with ctx.typing():
            for channel in guild.text_channels:
                # soon will add flag allowing all vs current
                if ch.id != channel.id:
                    continue
                try:
                    async for message in channel.history(limit=limit, oldest_first=False):
                        if not message.mentions:
                            continue

                        for member in message.mentions:
                            if member.id not in mentioned.keys():
                                mentioned[member.id] = dict(
                                    member=member,
                                    count=0
                                )
                            mentioned[member.id]["count"] += 1
                except Exception as e:
                    logger.exception(e)

        mentioned = list(mentioned.values())
        mentioned.sort(key=lambda x: x.get('count', 0), reverse=True)

        em = discord.Embed(
            title=guild.name,
            description=f"Most mentioned members in {ch.mention}",
            color=discord.Color.red()
        )
        em.set_footer(text=guild.name, icon_url=guild.icon_url)

        value = " - ".join([f"{m['member']} {m['count']}" for m in mentioned])
        if len(value) > 1000:
            value = value[:1000]

        em.add_field(name="Result", value=value)
        await ctx.send(embed=em)

    @dstats.command(name="mentioning")
    @checks.mod_or_permissions()
    async def dstats_mentioning(self, ctx: Context, limit=10000, days=7):
        """Count users that mention people the most."""
        guild = ctx.guild
        members = dict()
        ch = ctx.message.channel

        async with ctx.typing():
            for channel in guild.text_channels:
                # soon will add flag allowing all vs current
                if ch.id != channel.id:
                    continue
                try:
                    after = dt.datetime.utcnow() - dt.timedelta(days=days)
                    async for message in channel.history(limit=limit, after=after):
                        if not message.mentions:
                            continue

                        author = message.author

                        if author.id not in members.keys():
                            members[author.id] = dict(
                                member=author,
                                count=0
                            )
                        members[author.id]["count"] += 1

                except Exception as e:
                    logger.exception(e)

        mentioned = list(members.values())
        mentioned.sort(key=lambda x: x.get('count', 0), reverse=True)

        em = discord.Embed(
            title=guild.name,
            description=f"Members who mention others the most in {ch.mention} in last {days} days",
            color=discord.Color.red()
        )
        em.set_footer(text=guild.name, icon_url=guild.icon_url)

        value = " - ".join([f"{m['member']} {m['count']}" for m in mentioned])
        if len(value) > 1000:
            value = value[:1000]

        em.add_field(name="Result", value=value)
        await ctx.send(embed=em)

    @dstats.command(name="userwords")
    @checks.mod_or_permissions()
    async def dstats_user_words(self, ctx: Context, member: discord.Member, limit=10000, days=7):
        """Count word usage in channel"""
        guild = ctx.guild
        channel = ctx.channel
        async with ctx.typing():
            texts = []
            try:
                async for message in channel.history(limit=limit, oldest_first=False):
                    if message.author == member:
                        texts += [word.lower() for word in message.content.split(' ') if word not in stop_words]
            except Exception as e:
                logger.exception(e)

            mc = Counter(texts).most_common(100)

            em = discord.Embed(
                title=guild.name,
                description="Words used by {}".format(member.display_name),
                color=discord.Color.red()
            )
            em.set_footer(text=guild.name, icon_url=guild.icon_url)

            out = []
            for word, count in mc:
                m = re.match(r'^:([a-zA-Z\_]+):$', word)
                if m:
                    word = get_emoji(self.bot, m.group(1))
                out.append((word, count))

            name = "Word: Count"
            value = " - ".join(["{} {}".format(word, count) for word, count in out])
            if len(value) > 1000:
                value = value[:1000]

            em.add_field(name=name, value=value)
            await ctx.send(embed=em)

    @dstats.command(name="role")
    @checks.mod_or_permissions()
    async def dstats_role(self, ctx: Context, role: str, limit=10000, days=7):
        """Users by role."""
        async with ctx.typing():
            # search for role
            _role = None
            for r in ctx.guild.roles:
                if r.name.lower() == role.lower():
                    _role = r
                    break

            if _role is None:
                await ctx.send("Cannot find role. Aborted.")
                return

            # find members with role
            members = []
            for m in ctx.guild.members:
                if _role in m.roles:
                    members.append(m)

            if len(members) == 0:
                await ctx.send("Cannot find member with the role. Aborted.")
                return

            # list user stats
            for m in members:
                glog = GuildLog(ctx.guild)
                em = await glog.user_history_embed(m, days=days, limit=limit)
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
        p = parser()
        try:
            pargs = p.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return

        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            days = pargs.days
            limit = pargs.limit
            if limit == 0:
                limit = None
            text = pargs.text
            roles = get_guild_roles(ctx.guild, pargs.roles)
            embeds = await glog.channel_history_embeds(channel, days=days, limit=limit, roles=roles, text=text)
            for em in embeds:
                await ctx.send(embed=em)

    @dstats.command(name="channel_char_count")
    @checks.mod_or_permissions()
    async def dstats_channel_char_count(self, ctx: Context, channel: discord.TextChannel, *args):
        """Channel stats by character count.
        usage: [p]dstats [-h] [-r ROLES [ROLES ...]] [-t TOP] [-d DAYS] [-l LIMIT]

        optional arguments:
          -h, --help            show this help message and exit
          -r ROLES [ROLES ...], --roles ROLES [ROLES ...]
                                    Include roles
          -t TOP, --top TOP         Top N results
          -d DAYS, --days DAYS      Last N days
          -l LIMIT, --limit LIMIT   Limit N messages
        """
        p = parser()
        try:
            pargs = p.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return

        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            days = pargs.days
            limit = pargs.limit
            if limit == 0:
                limit = None
            text = pargs.text
            roles = get_guild_roles(ctx.guild, pargs.roles)
            embeds = await glog.channel_history_embeds(
                channel, days=days, limit=limit, roles=roles, text=text, enable_char_count=True
            )
            for em in embeds:
                await ctx.send(embed=em)

    @dstats.command(name="channels")
    @checks.mod_or_permissions()
    async def dstats_channels(self, ctx: Context, *args):
        """All users stats."""

        p = parser()
        try:
            pargs = p.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return

        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            days = pargs.days
            limit = pargs.limit
            text = pargs.text
            roles = get_guild_roles(ctx.guild, pargs.roles)
            channels = sorted(ctx.guild.text_channels, key=lambda x: x.position)

            for channel in channels:
                embeds = await glog.channel_history_embeds(channel, days=days, limit=limit, roles=roles, text=text)
                for em in embeds:
                    await ctx.send(embed=em)

    @dstats.command(name="server")
    @checks.mod_or_permissions()
    async def dstats_server(self, ctx: Context, *args):
        """Server stats by user."""
        async with ctx.typing():
            glog = GuildLog(ctx.guild)
            f = await glog.server_history()
            o = []

            for channel_id, count in f.get('channels', {}).items():
                msg = (
                    "{channel}: {count}".format(
                        channel=ctx.guild.get_channel(channel_id),
                        count=count
                    )
                )
                await ctx.send(msg)

    @dstats.command(name="users")
    @checks.mod_or_permissions()
    async def dstats_users(self, ctx: Context, *args):
        """Server stats by user."""
        p = parser()
        try:
            pargs = p.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return

        guild = ctx.guild

        async with ctx.typing():
            glog = GuildLog(guild)
            days = pargs.days
            text = pargs.text
            items = await glog.users_history(days=days, text=text)

            desc = "User activity in the last {} days".format(days)
            if text is not None and len(text) > 0:
                desc += ", containing `{}` ".format(text)
            em = discord.Embed(
                title=guild.name,
                description=desc,
                color=discord.Color.red()
            )
            em.set_footer(text=guild.name, icon_url=guild.icon_url)
            name = "User: Message Count"
            values = []
            for item in items[:100]:
                author = guild.get_member(item['author_id'])
                count = item['count']
                if author:
                    author_name = author.display_name
                else:
                    author_name = item['author_id']

                values.append('{}: {}'.format(author_name, count))

            value = ", ".join(values)
            if len(value) > 1000:
                value = value[:1000]

            em.add_field(name=name, value=value)
            await ctx.send(embed=em)
