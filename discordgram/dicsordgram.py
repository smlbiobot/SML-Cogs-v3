import discord
from redbot.core import Config
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red

IDENTIFIER = 20121208011605

class Discordgram(commands.Cog):
    """
    Simulate Instagram on Discord.
    Allows posting image to channel and reply via commands

    """

    def __init__(self, bot: Red):
        """Init."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=IDENTIFIER, force_registration=True)
        default_global = {
            "guilds": {}
        }
        default_guild = {}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @checks.mod_or_permissions()
    @commands.group()
    async def discordgramset(self, ctx):
        """Discordgram setttings."""
        pass

    @checks.mod_or_permissions()
    @discordgramset.command()
    async def discordgramset_channel(self, ctx):
        """Set channel."""
        guild = ctx.guild
        channel = ctx.channel
        async with self.config.guild(guild).guilds() as guilds:
            if guild.id not in guilds:
                guilds[guild.id] = dict(channel_id=None)
            channel_id = guilds.get(guild.id, {}).get('channel_id')
            if channel_id is not None:
                previous_channel = self.bot.get_channel(channel_id)
                await ctx.send(
                    f"Removed Discordgram from {previous_channel.mention}"
                )
            if channel_id == channel.id:
                guilds[guild.id]["channel_id"] = None
            else:
                guilds[guild.id]["channel_id"] = channel.id
                await ctx.send(
                    f"Discordgram channnel set to {channel.mention}"
                )


    @commands.guild_only()
    @commands.command(name="discordgramreply", aliases=["dgr"])
    async def discordgramreply(self, ctx, id, *, msg):
        pass
