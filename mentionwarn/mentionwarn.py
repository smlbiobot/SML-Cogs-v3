from typing import List
from typing import Optional

import discord
from discord import Embed
from discord import Member
from discord import Message
from pydantic import BaseModel
from redbot.core import checks
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

UNIQUE_ID = 202011120640


class WarnSetting(BaseModel):
    user_id: int
    guild_id: int
    message: str
    except_role_ids: Optional[List[int]] = None


class MentionWarn(commands.Cog):
    """
    Utility cog for warning people when specific users are mentioned.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {
            "warn_settings": {},
            "enabled": False,
        }
        self.config.register_guild(**default_guild)

    @commands.group()
    @checks.mod_or_permissions()
    async def mentionwarn(self, ctx):
        """Mention Warn Settings"""
        pass

    @checks.mod_or_permissions()
    @mentionwarn.command(name="toggle")
    async def toggle_settings(self, ctx: Context):
        """Toggle on/off for this server."""
        enabled = await self.config.guild(ctx.guild).enabled()
        enabled = not enabled
        await self.config.guild(ctx.guild).enabled.set(enabled)

        if enabled:
            await ctx.send("Warnings enabled")
        else:
            await ctx.send("Warnings disabled")

    @checks.mod_or_permissions()
    @mentionwarn.command(name="clear")
    async def clear_all_settings(self, ctx: Context):
        """Clear all settings for server."""
        msg = await ctx.send("Are you sure that you want to clear all the settings for this server?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is False:
            await ctx.send("Aborted")
            return

        async with self.config.guild(ctx.guild).warn_settings() as settings:
            if len(settings.keys()) > 0:
                await settings.clear()
                await ctx.send("Settings cleared")
            else:
                await ctx.send("No settings found (already cleared).")

    @checks.mod_or_permissions()
    @mentionwarn.command(name="list")
    async def list_settings(self, ctx: Context):
        """List all settings."""
        em = Embed(
            title="Mention Warns"
        )
        async with self.config.guild(ctx.guild).warn_settings() as settings:
            for user_id_str, v in settings.items():
                user = discord.utils.get(ctx.guild.members, id=int(user_id_str))
                ws = WarnSetting.parse_obj(v)
                value = f"{ws.message}\n"
                if ws.except_role_ids:
                    roles = [discord.utils.get(ctx.guild.roles, id=r_id) for r_id in ws.except_role_ids]
                    value += f"\nExcept roles:{' '.join([r.mention for r in roles])}"
                em.add_field(
                    name=str(user),
                    value=value,
                )
        await ctx.send(embed=em)

    def settings_embed(self, ctx: Context, ws: WarnSetting, title=None) -> Embed:
        em = Embed(
            title=title or "Warn Setting"
        )

        user = discord.utils.get(ctx.guild.members, id=ws.user_id)
        em.add_field(name="User", value=str(user))
        em.add_field(name="Message", value=ws.message)
        roles = "None"
        if ws.except_role_ids:
            except_roles = [discord.utils.get(ctx.guild.roles, id=r_id) for r_id in ws.except_role_ids]
            roles = " ".join([f"{r.mention}" for r in except_roles])
        em.add_field(name="Except Roles", value=roles)
        return em

    @checks.mod_or_permissions()
    @mentionwarn.command(name="add")
    async def add_settings(self, ctx: Context, user: Member, message: str, *except_role_names):
        """Add a warning setting except a role."""
        except_role_ids = None
        if except_role_names:
            except_roles = [discord.utils.get(ctx.guild.roles, name=r) for r in except_role_names]
            except_role_ids = [r.id for r in except_roles if r]

        ws = WarnSetting(
            user_id=user.id,
            guild_id=ctx.guild.id,
            message=message,
            except_role_ids=except_role_ids
        )

        async with self.config.guild(ctx.guild).warn_settings() as settings:
            if str(ws.user_id) in settings.keys():
                await ctx.send("User already exists. Please `edit` or `remove` the setting")
                return
            settings[str(ws.user_id)] = ws.dict()
            await ctx.send(embed=self.settings_embed(ctx, ws, title="Added New Setting"))

    @checks.mod_or_permissions()
    @mentionwarn.command(name="edit")
    async def edit_settings(self, ctx: Context, user: Member, message: str, *except_role_names):
        """Edit an existing settings."""
        async with self.config.guild(ctx.guild).warn_settings() as settings:
            if str(user.id) not in settings.keys():
                await ctx.send(f"Cannot find settings for {str(user)}")
                return

        except_role_ids = None
        if except_role_names:
            except_roles = [discord.utils.get(ctx.guild.roles, name=r) for r in except_role_names]
            except_role_ids = [r.id for r in except_roles if r]

        ws = WarnSetting(
            user_id=user.id,
            guild_id=ctx.guild.id,
            message=message,
            except_role_ids=except_role_ids
        )

        async with self.config.guild(ctx.guild).warn_settings() as settings:
            settings[str(ws.user_id)] = ws.dict()
            await ctx.send(embed=self.settings_embed(ctx, ws, title="Updated Setting"))

    @checks.mod_or_permissions()
    @mentionwarn.command(name="delete", alises=['remove', 'rm'])
    async def remove_settings(self, ctx: Context, user: Member):
        """Remove a setting about a user."""
        async with self.config.guild(ctx.guild).warn_settings() as settings:
            if str(user.id) not in settings.keys():
                await ctx.send(f"Cannot find settings for {str(user)}")
                return

            msg = await ctx.send("Please confirm that you want to delete this setting")
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            await ctx.bot.wait_for("reaction_add", check=pred)

            if pred.result is True:
                settings.pop(str(user.id), None)
                await ctx.send(f"Settings for {str(user)} removed")
            else:
                await ctx.send("Aborted")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        """Warn users when user is mentioned in settings"""
        channel = message.channel

        # iggnore bots
        if message.author.bot:
            return

        if not channel:
            return

        guild = channel.guild

        if not guild:
            return

        enabled = await self.config.guild(guild).enabled()
        if not enabled:
            return

        if not message.mentions:
            return

        if message.content.startswith('!'):
            return

        if message.content.startswith('?'):
            return

        mention_ids = [str(u.id) for u in message.mentions]

        def author_has_role(role_ids):
            author_role_ids = [role.id for role in message.author.roles]
            if len(set(author_role_ids).intersection(set(role_ids))) > 0:
                return True
            return False

        async with self.config.guild(guild).warn_settings() as settings:

            for mention_id in mention_ids:
                if mention_id in settings.keys():
                    ws = WarnSetting.parse_obj(settings[mention_id])
                    if ws.except_role_ids:
                        if author_has_role(ws.except_role_ids):
                            return

                    await channel.send(
                        f"{message.author.mention} {ws.message}"
                    )
