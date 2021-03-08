import asyncio
import datetime as dt
from typing import Optional

import discord
import humanfriendly
from discord.ext import tasks
from pydantic import BaseModel
from redbot.core import checks
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context

UNIQUE_ID = 20210308181241


class TimerConfig(BaseModel):
    channel_id: int
    message_id: Optional[int]
    timer_name: str
    timer_timestamp: int
    timer_iso: str

    def __init__(self, **data):
        timer_timestamp = data.pop('timer_timestamp', None)
        if not timer_timestamp:
            timer_timestamp = dt.datetime.fromisoformat(data.get('timer_iso')).timestamp()
        super().__init__(
            timer_timestamp=timer_timestamp,
            **data
        )

    def format_timespan(self, seconds, short=False):
        h = humanfriendly.format_timespan(int(seconds))
        if short:
            h = h.replace(' years', 'y')
            h = h.replace(' year', 'y')
            h = h.replace(' weeks', 'w')
            h = h.replace(' week', 'w')
            h = h.replace(' days', 'd')
            h = h.replace(' day', 'd')
            h = h.replace(' hours', 'h')
            h = h.replace(' hour', 'h')
            h = h.replace(' minutes', 'm')
            h = h.replace(' minute', 'm')
            h = h.replace(' seconds', 's')
            h = h.replace(' second', 's')
            h = h.replace(',', '')
            h = h.replace(' and', '')
            h = h.replace('  ', ' ')
        else:
            h = h.replace('week', 'wk')
            h = h.replace('hour', 'hr')
            h = h.replace('minute', 'min')
            h = h.replace('second', 'sec')
        return h

    def time_delta(self):
        now = dt.datetime.now(tz=dt.timezone.utc).timestamp()
        seconds = self.timer_timestamp - now
        return seconds

    def time_span(self):
        td = self.time_delta()
        if td < 0:
            s = f"-{self.format_timespan(-td, short=True)}"
        else:
            s = self.format_timespan(td, short=True)

        return s

    def embed(self) -> discord.Embed:
        seconds = self.time_delta()
        if seconds > 0:
            color = discord.Color.green()
        else:
            color = discord.Color.red()

        em = discord.Embed(
            title=self.timer_name,
            description=self.timer_iso,
            color=color,
            timestamp=dt.datetime.now(tz=dt.timezone.utc)
        )
        em.add_field(
            name='Countdown',
            value=self.time_span()
        )
        return em


class Timer(commands.Cog):
    """Timer"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {
            'timers': {},
        }
        self.config.register_guild(**default_guild)

    @property
    def periodic_tasks(self):
        return [
            self.run_periodic_task,
        ]

    async def initialize(self):
        for task in self.periodic_tasks:
            task.start()

    @checks.mod_or_permissions()
    @commands.group()
    async def timer(self, ctx):
        """Punish peope"""
        pass

    def make_key(self, config: TimerConfig):
        return f"t_{config.timer_name}-{config.channel_id}-{config.timer_timestamp}"

    def channel_id_from_key(self, channel_key):
        return channel_key[2:]

    @checks.is_owner()
    @timer.command(name="reset", pass_context=True)
    async def timer_reset(self, ctx: Context):
        """Reset all settings"""
        await self.config.clear_all_guilds()
        await ctx.send("Reset global config to defaults.")

    @checks.is_owner()
    @timer.command(name="settings", pass_context=True)
    async def timer_settings(self, ctx: Context):
        """Settings."""
        pass

    @checks.is_owner()
    @commands.guild_only()
    @timer.command(name="remove", pass_context=True)
    async def timer_remove(self, ctx: Context, timer_name: str):
        """Remove timer"""
        async with self.config.guild(ctx.guild).timers() as timers:
            for k, config in timers.copy().items():
                timer_config = TimerConfig.parse_obj(config)
                if timer_config.timer_name == timer_name:
                    timers.pop(k, None)
                    await ctx.send("Timer removed.")
                    return

        await ctx.send("Cannot find timer with that name.")

    @checks.is_owner()
    @commands.guild_only()
    @timer.command(name="add", pass_context=True)
    async def timer_add(self, ctx: Context, timer_name: str, iso_string: str, channel: discord.TextChannel = None):
        """Add timer"""
        if channel is None:
            channel = ctx.channel

        # add timezone
        if '+' not in iso_string:
            iso_string = f"{iso_string}+00:00"

        async with self.config.guild(ctx.guild).timers() as timers:
            config = TimerConfig(
                timer_name=timer_name,
                timer_iso=iso_string,
                channel_id=channel.id,
            )

            timer_key = self.make_key(config)

            timers[timer_key] = config.dict()

        await ctx.send("Added timer.")

    @tasks.loop(seconds=10)
    async def run_periodic_task(self):
        for guild in self.bot.guilds:
            async with self.config.guild(guild).timers() as timers:
                to_remove_keys = []
                for k, config in timers.copy().items():
                    timer_config = TimerConfig.parse_obj(config)

                    # remove timer if channel does not exist
                    channel = discord.utils.get(guild.channels, id=timer_config.channel_id)
                    if not channel:
                        to_remove_keys.append(k)
                        continue

                    # create message if needed
                    if timer_config.message_id is None:
                        message = await channel.send(embed=timer_config.embed())
                        timer_config.message_id = message.id

                        timers[k] = timer_config.dict()
                    else:
                        try:
                            message = await channel.fetch_message(timer_config.message_id)
                        except discord.NotFound:
                            to_remove_keys.append(k)
                            continue

                        await message.edit(embed=timer_config.embed())
                if to_remove_keys:
                    for k in to_remove_keys:
                        timers.pop(k, None)

        # wait til the next minute
        # delta = dt.timedelta(minutes=1)
        # now = dt.datetime.now()
        # next_minute = (now + delta).replace(microsecond=0, second=0)
        #
        # wait_seconds = (next_minute - now).seconds
        # if wait_seconds < 10:
        #     await asyncio.sleep(wait_seconds)

    @run_periodic_task.before_loop
    async def before_run_mention_member_task(self):
        await self.bot.wait_until_red_ready()
