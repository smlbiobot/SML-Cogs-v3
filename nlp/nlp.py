import itertools

from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from textblob import TextBlob
from textblob.sentiments import NaiveBayesAnalyzer
from discord import Embed

IDENTIFIER = 20210813172739


def grouper(n, iterable, fillvalue=None):
    """Helper function to split lists.

    Example:
    grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return (
        [e for e in t if e is not None]
        for t in itertools.zip_longest(*args))


class NaturalLanguageProcessingCog(commands.Cog):
    """Member Management plugin for Red Discord bot."""

    def __init__(self, bot: Red):
        """Init."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=IDENTIFIER, force_registration=True)
        default_global = {}
        default_guild = {}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @commands.guild_only()
    @commands.group()
    async def nlp(self, ctx):
        """SML utility functions"""
        pass

    @nlp.command(name="sentiment", aliases=['sent'])
    async def sentiment(self, ctx, *, txt):
        """
        Sentiment analysis
        :param ctx:
        :param txt:
        :return:
        """
        async with ctx.typing():
            blob = TextBlob(txt, analyzer=NaiveBayesAnalyzer())
            sent = blob.sentiment

            embed = Embed(
                title="Sentiment Analysis",
                description=txt,
            )

            embed.add_field(
                name="Classificiation",
                value=sent.classification,
                inline=False,
            )
            embed.add_field(
                name="p_pos",
                value=sent.p_pos,
                inline=False,
            )
            embed.add_field(
                name="p_neg",
                value=sent.p_neg,
                inline=False,
            )

        await ctx.send(embed=embed)
