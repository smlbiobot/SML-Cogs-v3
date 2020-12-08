import discord
from redbot.core import Config
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from discord import Message
from discord import Embed
from pydantic import BaseModel
import datetime as dt

IDENTIFIER = 20121208011605


class DGMessage(BaseModel):
    discordgram_id: int
    message_id: int
    author_id: int
    bot_message_id: int

    @classmethod
    def make_message(cls, *, message: Message, discordgram_id: int, bot_message: Message):
        return DGMessage(
            discordgram_id=discordgram_id,
            message_id=message.id,
            author_id=message.author.id,
            bot_message_id=bot_message.id
        )


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
        default_global = {}
        default_guild = {
            'channel_id': None,
            'messages': [],
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @checks.mod_or_permissions()
    @commands.group()
    async def discordgramset(self, ctx):
        """Discordgram setttings."""
        pass

    @checks.mod_or_permissions()
    @discordgramset.command(name="channel")
    async def discordgramset_channel(self, ctx):
        """Set channel."""
        guild = ctx.guild
        channel = ctx.channel

        channel_id = await self.config.guild(guild).channel_id()

        if channel_id is not None:
            previous_channel = self.bot.get_channel(channel_id)
            await ctx.send(
                f"Removed Discordgram from {previous_channel.mention}"
            )

        if channel_id == channel.id:
            channel_id = None
        else:
            channel_id = channel.id
            await ctx.send(
                f"Discordgram channnel set to {channel.mention}"
            )

        await self.config.guild(guild).channel_id.set(channel_id)

    @commands.guild_only()
    @commands.command(name="discordgramreply", aliases=["dgr"])
    async def discordgramreply(self, ctx, id, *, msg):
        pass

    @commands.guild_only()
    @commands.Cog.listener(name="on_message")
    async def on_message(self, message: discord.Message):
        """Monitor activity if messages posted in Discordgram channel."""
        guild = message.guild

        if guild is None:
            return

        channel = message.channel
        channel_id = await self.config.guild(guild).channel_id()
        if channel_id is None:
            return
        if channel_id != channel.id:
            return
        if message.author.bot:
            return

        attachments = message.attachments
        if not attachments:
            await message.delete()
            return

        author = message.author

        messages = await self.config.guild(guild).messages()
        dgr_id = len(messages)
        description = (
            f"Type `!dgr {dgr_id} [your reply]`"
            f"to reply to {author.display_name}"
        )

        em = Embed(
            description=description
        )
        bot_message = await channel.send(embed=em)

        dgm = DGMessage.make_message(
            message=message,
            discordgram_id=dgr_id,
            bot_message=bot_message
        )
        async with self.config.guild(guild).messages() as messages:
            messages.append(dgm.dict())

    @commands.command(name="discordgramreply", aliases=['dgr'])
    async def discordgramreply(self, ctx, discordgram_id, *, msg):
        """Reply to Discordgram by ID."""
        guild = ctx.guild
        channel_id = await self.config.guild(guild).channel_id()
        if channel_id is None:
            return

        try:
            discordgram_id = int(discordgram_id)
        except ValueError:
            bot_msg = await ctx.send("discordgram_id must be a number")
            await bot_msg.delete(delay=5)
            return

        author = ctx.author
        messages = await self.config.guild(guild).messages()
        if discordgram_id >= len(messages):
            bot_msg = await ctx.send("This is not a valid Discordgram id")
            await bot_msg.delete(delay=5)
            return

        message = None
        for m in messages:
            if m.get('discordgram_id') == discordgram_id:
                message = m

        if message is None:
            bot_msg = await ctx.send("Cannot find the discordgram")
            await bot_msg.delete(delay=5)
            return

        # message = messages[discordgram_id]
        channel = self.bot.get_channel(channel_id)
        dg_message = DGMessage.parse_obj(message)

        bot_msg = await channel.fetch_message(dg_message.bot_message_id)

        em = bot_msg.embeds[0]
        em.add_field(
            name=author.display_name,
            value=msg
        )
        em.timestamp = dt.datetime.now(tz=dt.timezone.utc)

        await bot_msg.edit(embed=em)
