import asyncio
import random

import discord
from discord.ext import tasks
from redbot.core import checks
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context

UNIQUE_ID = 20210304172743


def random_text():
    return random.choice([
        'Stop tagging people for stupid shit.',
        'This is what you get for randomly tagging people.',
        'Don’t do this ever again.',
        'Repeat offenders will be kicked / banned from this server.',
        'I hope that you have learned your lesson.',
        'Plea to a mod to stop this.'
    ])


class Punish(commands.Cog):
    """Punish"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {
            'mention': {},
            'dm': {}
        }
        self.config.register_guild(**default_guild)

    @property
    def periodic_tasks(self):
        return [
            self.run_mention_member_task,
        ]

    async def initialize(self):
        await self.bot.wait_until_red_ready()
        # for task in self.periodic_tasks:
        #     task.add_exception_type(
        #
        #     )

        for task in self.periodic_tasks:
            task.start()

    @checks.mod_or_permissions()
    @commands.group()
    async def punish(self, ctx):
        """Punish peope"""
        pass

    def make_key(self, member_id):
        return f"m_{member_id}"

    def member_id_from_key(self, member_key):
        return member_key[2:]

    @checks.mod_or_permissions()
    @punish.command(name="mention", pass_context=True)
    async def punish_mention(self, ctx: Context, member: discord.Member):
        """Punish users by having the bot randomly mention them."""
        async with self.config.guild(ctx.guild).mention() as mention:
            if self.make_key(member.id) in mention:
                mention.pop(self.make_key(member.id), None)
                await ctx.send(f"Disabled punish for {member}")
            else:
                mention[self.make_key(member.id)] = ctx.channel.id
                await ctx.send("Added user to random mentions.")

    @checks.mod_or_permissions()
    @punish.command(name="reset", pass_context=True)
    async def punish_reset(self, ctx: Context):
        """Reset all settings"""
        await self.config.clear_all_guilds()
        await ctx.send("Reset server config to defaults.")

    @checks.mod_or_permissions()
    @punish.command(name="settings", pass_context=True)
    async def punish_settings(self, ctx: Context):
        """Show active punishments."""
        o = [
            "List of active punishes"
        ]

        async with self.config.guild(ctx.guild).mention() as mention:
            print(mention)
            for member_key, channel_id in mention.items():
                member_id = self.member_id_from_key(member_key)
                try:
                    member = ctx.guild.get_member(int(member_id))
                except ValueError as e:
                    print(mention)
                    continue

                try:
                    channel = ctx.guild.get_channel(int(channel_id))
                except ValueError as e:
                    print(mention)
                    continue

                if all([member, channel]):
                    o.append(f"{channel.mention} {member.mention}")

        o.append(
            f"Count: {len(o) - 1}"
        )

        await ctx.send("\n".join(o))

    @tasks.loop(seconds=5)
    async def run_mention_member_task(self):
        TASK_SLEEP = 5
        for guild in self.bot.guilds:
            async with self.config.guild(guild).mention() as mention:
                if not mention:
                    continue
                for member_key, channel_id in mention.items():
                    member_id = self.member_id_from_key(member_key)
                    try:
                        member = guild.get_member(int(member_id))
                    except ValueError as e:
                        print(mention)
                        continue

                    try:
                        channel = guild.get_channel(int(channel_id))
                    except ValueError as e:
                        print(mention)
                        continue

                    content = f"{member.mention} {random_text()}"
                    if not all([member, channel]):
                        continue
                    await asyncio.sleep(TASK_SLEEP * 0.5 * random.random())
                    await channel.send(content)

    @run_mention_member_task.before_loop
    async def before_run_mention_member_task(self):
        await self.bot.wait_until_red_ready()
