import os
from typing import Optional

import discord
from discord import Guild
from redbot.cogs.cleanup import Cleanup
from redbot.cogs.cleanup.converters import PositiveInt
from redbot.core import checks
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.mod import mass_purge

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

    @sml.command(name="usertest", aliases=['ut'])
    @commands.is_owner()
    async def usertest(self, ctx: Context, number):
        """
        Show prototypes based on number
        :param ctx:
        :param number:
        :return:
        """
        urls = {
            '1': 'https://xd.adobe.com/view/a66f240b-05f9-4b0f-b8ac-7d60f6339420-f33c',
            '2': 'https://xd.adobe.com/view/2475a1bd-4985-4aa1-8f32-8ce1c7c28ecd-7126',
            '3': 'https://xd.adobe.com/view/b87ce6ba-3e0c-4411-b412-2cdd44060365-ed2f',
        }
        url = urls.get(number)

        if not url:
            await ctx.send("Invalid number")
            pass

        await ctx.send(url)

    @sml.command(name='sho')
    async def sho_add_2v2(self, ctx: Context, member: discord.Member = None):
        """
        Allow Sho to add 2v2 role for member
        :param ctx:
        :param member:
        :return:
        """
        if ctx.author.id not in [
            321151175292485632,  # show
            209287691722817536,  # sml
        ]:
            await ctx.send("You don‘t have permission to run this command")
            return

        if member is None:
            await ctx.send("You must include a member")
            return

        role = discord.utils.get(ctx.guild.roles, name='RR.2v2.SHO')
        await member.add_roles(role, reason="SHO 2v2 member add")
        await ctx.send(f"Added {str(role)} to {member.mention}")

    @sml.command(name="sayc")
    @commands.guild_only()
    @checks.mod_or_permissions()
    async def sayc(self, ctx, channel: discord.TextChannel, *, msg):
        """Have bot say stuff in channel. Remove command after run."""
        await channel.send(msg)

    @sml.command(name="cleanupuser")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def cleanup_user_messages(self, ctx: Context, user: str, number: PositiveInt, delete_pinned: bool = False):
        """
        Delete [number] of messages from user in all channels
        """

        member = None
        try:
            member = await commands.MemberConverter().convert(ctx, user)
        except commands.BadArgument:
            try:
                _id = int(user)
            except ValueError:
                raise commands.BadArgument()
        else:
            _id = member.id

        def check(m):
            if m.author.id == _id:
                return True
            else:
                return False

        number = int(number)

        async with ctx.typing():
            await ctx.send("If you have many channels, this could take a while to complete…")
            for channel in ctx.guild.channels:
                try:
                    to_delete = await Cleanup.get_messages_for_deletion(
                        channel=channel,
                        number=number,
                        check=check,
                        before=ctx.message,
                        delete_pinned=delete_pinned,
                    )
                except AttributeError:
                    # AttributeError: 'CategoryChannel' object has no attribute 'history'
                    pass
                else:
                    if to_delete:
                        await mass_purge(to_delete, channel)

            await ctx.send("Completed.")

    @commands.command(name="avatar")
    async def avatar(self, ctx: Context, member: discord.Member = None):
        if member is None:
            member = ctx.author

        try:
            await ctx.send(
                member.avatar_url_as(
                    format='png',
                    size=2048,
                )
            )
        except discord.InvalidArgument:
            pass


