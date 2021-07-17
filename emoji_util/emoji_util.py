from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context

UNIQUE_ID = 20210717191549

import flag


class EmojiUtil(commands.Cog):
    """Flag"""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {
        }
        self.config.register_guild(**default_guild)

    @commands.group()
    async def emoji(self, ctx):
        """Emoji utilities"""
        pass

    @emoji.command("flag")
    async def flag(self, ctx: Context, *countries):
        """
        Convert country iso code to emojis
        :param countries:
        :return:
        """
        emojis = []
        for c in countries:
            try:
                e = flag.flag(c.upper())
            except ValueError:
                e = ""
            emojis.append(e)

        out = " ".join(emojis)

        await ctx.send(f"```{out}```")
