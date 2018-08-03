import argparse

import discord
from discord.ext import commands
from redbot.core import checks
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.chat_formatting import pagify


def audit_parser():
    """Argument parser."""
    parser = argparse.ArgumentParser(prog='[p]audit')
    parser.add_argument(
        '-l', '--limit',
        help='Limit N messages',
        type=int,
        default=10
    )
    parser.add_argument(
        '-r', '--reverse',
        help='If set to true, return entries in oldest->newest order',
        type=bool,
        default=False
    )
    return parser


class Audit:
    """Server audit logs."""

    def __init__(self, bot: Red):
        """Init."""
        self.bot = bot

    @commands.guild_only()
    @commands.group()
    @checks.mod_or_permissions()
    async def audit(self, ctx: Context):
        """Audit log."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @audit.command(name="channel_update")
    @checks.mod_or_permissions()
    async def audit_channel_update(self, ctx: Context, *args):
        """User stats."""
        p = audit_parser()
        try:
            pargs = p.parse_args(args)
        except SystemExit:
            await ctx.send_help()
            return
        async with ctx.typing():
            out = ['discord.AuditLogAction.channel_update']
            async for entry in ctx.guild.audit_logs(limit=pargs.limit, reverse=pargs.reverse,
                                                    action=discord.AuditLogAction.channel_update):
                try:
                    user = entry.user.name
                    created_at = entry.created_at.strftime("%Y-%m-%d %H:%M")
                    target = entry.target
                    if isinstance(target, discord.object.Object):
                        target = "discord.object"

                    target = str(target)

                    line = "{user:10.10} | {target:16.16} | {created_at}".format(
                        user=user,
                        target=target,
                        created_at=created_at
                    )
                    out.append(line)

                    for item in iter(entry.after):
                        out.append("{:10.10} : {:40.40}".format(item[0], item[1]))
                    out.append(".")


                except Exception as e:
                    pass

            for page in pagify("\n".join(out)):
                await ctx.send(box(page))
