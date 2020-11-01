import discord
from discord import TextChannel
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context

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


    @commands.mod_or_permissions()
    @commands.group()
    async def sml(self, ctx):
        """SML utility functions"""
        pass

    @sml.command(name="estpruned")
    async def estimate_pruned_members(self, ctx:Context, days:int=30):
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



