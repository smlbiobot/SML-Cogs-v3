import discord
from discord import Message
from redbot.core import checks
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red

UNIQUE_ID = 20210108201038


class AutoTranslate(commands.Cog):
    """
    Automatically translate channel messages using Google Translate

    Depend on https://github.com/TrustyJAID/Trusty-cogs/blob/master/translate
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {
            "translate_channels": {},
        }
        self.config.register_guild(**default_guild)

    @commands.group()
    @checks.is_owner()
    async def autotranslateset(self, ctx: commands.Context) -> None:
        pass

    @autotranslateset.command(name="list")
    @checks.is_owner()
    async def list_auto_translate_channels(self, ctx: commands.Context) -> None:
        em = discord.Embed(
            title="Auto Translation channels",
        )
        async with self.config.guild(ctx.guild).translate_channels() as channels:
            for channel_id, languages in channels.copy().items():
                channel = ctx.guild.get_channel(int(channel_id))
                if languages:
                    em.add_field(
                        name=channel,
                        value=", ".join(languages)
                    )
                else:
                    channels.pop(channel_id)
        await ctx.send(embed=em)

    @autotranslateset.command(name="toggle")
    @checks.is_owner()
    async def toggle_auto_translate(self, ctx: commands.Context, *languages):
        """
        Toggle auto translate for language(s) in channel.
        """
        await ctx.send(
            "IMPORTANT: This can get expensive ($20 / million characters). "
            "Character count multiply per languages selected. "
            "Don’t enable if you don’t know what you’re doing. "
        )
        async with self.config.guild(ctx.guild).translate_channels() as channels:
            if channels.get(str(ctx.channel.id)) is None:
                channels[ctx.channel.id] = languages
                await ctx.send(
                    f"Auto-translating messages to {', '.join(languages)}"
                )
            else:
                channels.pop(str(ctx.channel.id), None)
                await ctx.send(
                    f"Disable auto-translation for channel."
                )

    @commands.Cog.listener(name="on_message_without_command")
    async def on_message(self, message: Message):
        """
        Auto translate on message
        :return:
        """
        try:
            guild = message.guild
        except AttributeError:
            return

        if not guild:
            return

        if not message.channel:
            return

        if message.author.bot:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        async with self.config.guild(guild).translate_channels() as channels:
            languages = channels.get(str(message.channel.id))
            if not languages:
                return

        translate_cog = self.bot.get_cog('Translate')

        if not translate_cog:
            return

        if not isinstance(languages, list):
            return

        ctx = commands.Context(
            message=message,
            prefix='UNUSED_IGNORE',
        )

        msg = message.content

        try:
            detected_lang = await translate_cog.detect_language(msg)
        except Exception as e:
            # ignore errors
            return

        to_languages = [l for l in languages if detected_lang[0][0]["language"] != l]

        for lang in to_languages:
            await translate_cog.translate(
                ctx,
                lang,
                message=message.content
            )
