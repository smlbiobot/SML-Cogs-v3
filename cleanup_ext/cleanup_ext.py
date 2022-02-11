import re
from typing import Optional
from typing import Union

import discord
from discord.ext import commands as dpy_commands
from discord.ext.commands.errors import BadArgument
from redbot.cogs.cleanup import Cleanup
from redbot.cogs.cleanup.converters import PositiveInt
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.mod import mass_purge

UNIQUE_ID = 20211211023313

ID_REGEX = re.compile(r"([0-9]{15,20})")
USER_MENTION_REGEX = re.compile(r"<@!?([0-9]{15,21})>$")


class RawUserIdConverter(dpy_commands.Converter):
    """
    Converts ID or user mention to an `int`.
    Useful for commands like ``[p]ban`` or ``[p]unban`` where the bot is not necessarily
    going to share any servers with the user that a moderator wants to ban/unban.
    This converter doesn't check if the ID/mention points to an actual user
    but it won't match IDs and mentions that couldn't possibly be valid.
    For example, the converter will not match on "123" because the number doesn't have
    enough digits to be valid ID but, it will match on "12345678901234567" even though
    there is no user with such ID.
    """

    async def convert(self, ctx: "Context", argument: str) -> int:
        # This is for the hackban and unban commands, where we receive IDs that
        # are most likely not in the guild.
        # Mentions are supported, but most likely won't ever be in cache.

        if match := ID_REGEX.match(argument) or USER_MENTION_REGEX.match(argument):
            return int(match.group(1))

        raise BadArgument(_("'{input}' doesn't look like a valid user ID.").format(input=argument))


class CleanupExt(commands.Cog):
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)

    @commands.mod_or_permissions(manage_messages=True)
    @commands.group('cleanupext')
    async def cleanupext(self, ctx):
        """Cleanup extension"""
        pass

    @commands.mod_or_permissions(manage_messages=True)
    @commands.group(name='multicleanup', aliases=['mcleanup'])
    async def multicleanup(self, ctx: Context):
        """Multi-channel cleanup"""
        pass

    @commands.mod_or_permissions(manage_messages=True)
    @multicleanup.command(name="user")
    async def multicleanup_user(
            self,
            ctx: Context,
            user: Union[discord.Member, RawUserIdConverter],
            number: Optional[PositiveInt],
            delete_pinned: bool = False,
    ):
        """Delete the last X messages from a specified user from entire server."""

        member = None
        if isinstance(user, discord.Member):
            member = user
            _id = member.id
        else:
            _id = user

        def check(m):
            if m.author.id == _id:
                return True
            else:
                return False

        author = ctx.author

        for channel in ctx.guild.text_channels:
            to_delete = await Cleanup.get_messages_for_deletion(
                channel=channel,
                number=PositiveInt(number),
                check=check,
                before=ctx.message,
                delete_pinned=delete_pinned,
            )
            reason = (
                "{}({}) deleted {} messages"
                " made by {}({}) in channel #{}."
                "".format(
                    author.name,
                    author.id,
                    humanize_number(len(to_delete), override_locale="en_US"),
                    member or "???",
                    _id,
                    ctx.guild.name,
                )
            )

            await mass_purge(to_delete, channel)
