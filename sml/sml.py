import os

from discord import Guild
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context
from typing import Optional
import discord

UNIQUE_ID = 202011010631


class SML(commands.Cog):
    """
    Utility cog for SML until more suitable collection can be found.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {}
        self.config.register_guild(**default_guild)

    @commands.group()
    async def sml(self, ctx):
        """SML utility functions"""
        pass

    @sml.command(name="estpruned")
    @commands.mod_or_permissions()
    async def estimate_pruned_members(self, ctx: Context, days: int = 30):
        """
        Estimate the number of members that will be pruned by the prune command
        :param ctx:
        :param days:
        :return:
        """
        async with ctx.typing():
            n = await ctx.guild.estimate_pruned_members(days=days)
            await ctx.send(
                f"**{n}** members will be pruned from the server "
                f"if prune is run against members who have not been active "
                f"in the last {days} days."
            )

    @sml.command(name="emoji")
    @commands.is_owner()
    async def uplaod_emoji(self, ctx: Context, local_folder: str = None, guild_ids: str = None):
        """
        Upload local folder of images to a list of guilds
        Checking first that guild does not have the same emoji
        if guild is full then upload to the next on the list

        """
        guild_ids = guild_ids.split(',')

        def emoji_exist(name):
            for guild_id in guild_ids:
                guild = self.bot.get_guild(int(guild_id))
                for em in guild.emojis:
                    if str(em.name) == str(name):
                        return True
            return False

        def get_available_guild() -> Optional[Guild]:
            for guild_id in guild_ids:
                guild = self.bot.get_guild(int(guild_id))
                if len(guild.emojis) >= guild.emoji_limit:
                    continue

                return guild
            return None

        for file in os.listdir(local_folder):
            name, ext = os.path.splitext(file)

            if emoji_exist(name):
                continue

            guild = get_available_guild()
            if guild is None:
                continue

            try:
                filepath = os.path.join(local_folder, file)
                with open(filepath, 'rb') as f:
                    await guild.create_custom_emoji(
                        name=name,
                        image=f.read()
                    )
            except discord.Forbidden:
                await ctx.send("Forbiddeen")
            except discord.HTTPException:
                await ctx.send("HTTPException")
            else:
                await ctx.send(f"Created {name} at {guild.name}")

            # await ctx.send(f"{name} - {ext}")
