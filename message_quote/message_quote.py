import discord
from discord import TextChannel
from discord.ext.commands.converter import TextChannelConverter
from discord.ext.commands.errors import BadArgument
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import commands

UNIQUE_ID = 202011012214


class MessageQuote(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)

    @commands.command(name="mq")
    async def message_quote(self, ctx, *, args):
        """
        Quote message(s) by ID

        !mq 582794656560054272
        !mq 582794656560054272 #family-chat
        !mq 582794656560054272 582794656560054273 #family-chat
        If channel is omitted, use current channel
        """
        args = args.split(" ")
        last_arg = args[-1]

        converter = TextChannelConverter()
        try:
            channel = await converter.convert(ctx, last_arg)
        except BadArgument:
            channel = None
        else:
            args = args[:-1]
        if channel is None:
            channel = ctx.message.channel

        message_ids = args

        await self._show_message(ctx, channel, message_ids)

    async def _show_message(self, ctx, channel: TextChannel, message_ids):
        messages = []
        for message_id in message_ids:
            try:
                msg = await channel.fetch_message(message_id)
            except discord.NotFound:
                await self.bot.say("Message not found.")
                return
            except discord.Forbidden:
                await self.bot.say("I do not have permissions to fetch the message")
                return
            except discord.HTTPException:
                await self.bot.say("Retrieving message failed")
                return

            if not msg:
                continue

            messages.append(msg)

        for msg in messages:

            link = f'https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}'

            em = discord.Embed(
                title="Quote",
                description=msg.content,
                url=link
            )

            if msg.attachments:
                url = msg.attachments[0].url
                if url:
                    em.set_image(url=url)

            em.add_field(
                name="Author",
                value=msg.author.mention,
                inline=False
            )

            em.add_field(
                name="Channel",
                value=msg.channel.mention,
                inline=False
            )

            em.add_field(
                name="Posted",
                value=msg.created_at.isoformat(sep=" "),
                inline=False
            )

            if msg.edited_at:
                em.add_field(
                    name="Edited",
                    value=msg.edited_at.isoformat(sep=" "),
                    inline=False
                )

            em.set_footer(
                text=msg.guild.name,
                icon_url=msg.guild.icon_url
            )

            await ctx.send(embed=em)
