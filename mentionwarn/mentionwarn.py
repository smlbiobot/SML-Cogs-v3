from typing import List
from typing import Optional

import discord
from discord import Embed
from discord import Member
from discord import Role
from pydantic import BaseModel
from redbot.core import checks
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Context

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
            "warn_settings": {}
        }
        self.config.register_guild(**default_guild)

    @commands.group()
    @checks.mod_or_permissions()
    async def mentionwarnset(self, ctx):
        """Mention Warn Settings"""
        pass

    @mentionwarnset.command(name="clear")
    async def clear_all_settings(self, ctx: Context):
        async with self.config.guild(ctx.guild).warn_settings() as settings:
            if settings:
                await settings.clear()
            await ctx.send("Settings cleared")

    @mentionwarnset.command(name="add")
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
        await ctx.send(str(ws.dict()))
        async with self.config.guild(ctx.guild).warn_settings() as settings:
            print(settings)
            if str(ws.user_id) in settings.keys():
                await ctx.send("User already exists. Please `edit` or `remove` the setting")
                return

            settings[str(ws.user_id)] = ws.dict()
            await ctx.send("Config added")

    @mentionwarnset.command(name="list")
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
