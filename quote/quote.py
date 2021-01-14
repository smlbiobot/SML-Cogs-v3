import json
from typing import Literal

import aiohttp
import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.config import Config
from pydantic import BaseModel
import datetime as dt
from typing import Optional
import re

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class QuoteItem(BaseModel):
    key: str
    text: str
    author_id: Optional[int] = None
    timestamp: Optional[dt.datetime] = None

    @property
    def urls(self):
        urls = re.findall(
            f'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            self.text
        )
        return urls


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class Quote(commands.Cog):
    """
    Add and display text as quotes
    """

    RESERVED_WORDS = [
        'a',
        'add',
        'r',
        'rm',
        'remove',
        'l',
        'list',
        'e',
        'edit',
    ]

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=20210114134400,
            force_registration=True,
        )
        default_global = {

        }
        default_guild = {
            "allowed_role_ids": [],
            "quotes": {},
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        await super().red_delete_data_for_user(requester=requester, user_id=user_id)

    async def current_settings_embed(self, guild=None):
        em = discord.Embed(title="Quote Settings")
        async with self.config.guild(guild).allowed_role_ids() as allowed_role_ids:
            roles = [
                discord.utils.get(guild.roles, id=role_id) for role_id in allowed_role_ids
            ]
            for role, role_id in zip(roles, allowed_role_ids):
                if not role:
                    allowed_role_ids.remove(role_id)

            if allowed_role_ids:
                value = " ".join([
                    discord.utils.get(guild.roles, id=role_id).mention for role_id in allowed_role_ids
                ])
            else:
                value = 'None'

            em.add_field(
                name="Allowed Roles",
                value=value
            )

        return em

    @commands.group(aliases=['qs'])
    async def quoteset(self, ctx: Context):
        """Quote Settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=await self.current_settings_embed(ctx.guild))

    @quoteset.command(name="import")
    @checks.is_owner()
    async def quoteset_import(self, ctx: Context):
        """Import old data."""
        if not ctx.message.attachments:
            await ctx.send("You must include a JSON attachment")
            return

        attach = ctx.message.attachments[0]
        url = attach.url

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        async with self.config.guild(ctx.guild).quotes() as quotes:
            for k, v in data.items():
                key = k.lower()

                item = QuoteItem(
                    key=key,
                    text=v,
                )
                quotes[key] = json.loads(item.json())

    @quoteset.command(name="addrole")
    @checks.mod_or_permissions(manage_roles=True)
    async def quoteset_addrole(self, ctx: Context, role_name):
        """Add a server role that is allowed to add quotes."""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send("Can’t find role on this server.")
            return

        async with self.config.guild(ctx.guild).allowed_role_ids() as allowed_role_ids:
            if role.id not in allowed_role_ids:
                allowed_role_ids.append(role.id)

        await ctx.send(embed=await self.current_settings_embed(ctx.guild))

    @quoteset.command(name="removerole")
    @checks.mod_or_permissions(manage_roles=True)
    async def quoteset_removerole(self, ctx: Context, role_name):
        """Remove a server role that is allowed to add quotes."""
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send("Can’t find role on this server.")
            return

        async with self.config.guild(ctx.guild).allowed_role_ids() as allowed_role_ids:
            if role.id in allowed_role_ids:
                allowed_role_ids.remove(role.id)
                await ctx.send(f"Removed {role} from list of allowed roles.")
            else:
                await ctx.send("Cannot find this role in list of allowed roles.")

        await ctx.send(embed=await self.current_settings_embed(ctx.guild))

    async def can_run_command(self, ctx: Context) -> bool:
        async with self.config.guild(ctx.guild).allowed_role_ids() as allowed_role_ids:
            for role in ctx.author.roles:
                if role.id in allowed_role_ids:
                    return True
        return False

    @quoteset.command(name="add", aliases=['a'])
    async def quoteset_add(self, ctx: Context, name, *, text):
        """Add a quote."""
        if not await self.can_run_command(ctx):
            await ctx.send("You don’t have permission to run this command")
            return

        name = name.lower()

        if name in ['list', 'l']:
            await ctx.send("You cannot name a quote with this name.")
            return

        async with self.config.guild(ctx.guild).quotes() as quotes:
            if name in quotes.keys():
                await ctx.send(
                    f"{name} already exists. Use edit to edit the quote."
                )
                return

            item = QuoteItem(
                key=name,
                text=text,
                author_id=ctx.author.id,
                timestamp=dt.datetime.now(dt.timezone.utc)
            )
            quotes[name] = json.loads(item.json())

        await ctx.send("Quote saved.")

    @quoteset.command(name="edit", aliases=['e'])
    async def quoteset_edit(self, ctx: Context, name, *, text):
        """Edit a quote"""
        if not await self.can_run_command(ctx):
            await ctx.send("You don’t have permission to run this command")
            return

        name = name.lower()

        async with self.config.guild(ctx.guild).quotes() as quotes:
            item = QuoteItem(
                key=name,
                text=text,
                author_id=ctx.author.id,
                timestamp=dt.datetime.now(dt.timezone.utc)
            )
            quotes[name] = json.loads(item.json())

        await ctx.send("Quote updated.")

    @quoteset.command(name="remove", aliases=['r', 'rm'])
    async def quoteset_remove(self, ctx: Context, name):
        """Remove a quote"""
        if not await self.can_run_command(ctx):
            await ctx.send("You don’t have permission to run this command")
            return

        name = name.lower()

        async with self.config.guild(ctx.guild).quotes() as quotes:
            q = quotes.pop(name, None)
            if q is None:
                await ctx.send("No quotes with that name")
                return

        await ctx.send("Quote removed.")

    async def available_votes_embed(self, guild) -> discord.Embed:
        em = discord.Embed()
        async with self.config.guild(guild).quotes() as quotes:
            keys = sorted(quotes.keys())
            if not keys:
                em.add_field(
                    name="Quote names",
                    value="None"
                )
            else:
                for group in chunks(keys, 20):
                    em.add_field(
                        name=".",
                        value=", ".join(group),
                        inline=False
                    )

        return em

    @quoteset.command(name="list", aliases=['l'])
    async def quoteset_list(self, ctx: Context):
        """List available quotes"""
        await ctx.send(embed=await self.available_votes_embed(ctx.guild))

    @commands.command(aliases=['q'])
    async def quote(self, ctx: Context, name):
        """Display a quote.

        Use !qs list to see a list of quotes.
        """
        name = name.lower()
        async with self.config.guild(ctx.guild).quotes() as quotes:
            raw = quotes.get(name)
            if not raw:
                await ctx.send("Cannot find quote with that name")
                await ctx.send(embed=await self.available_votes_embed(ctx.guild))
                return

            item = QuoteItem.parse_obj(raw)

            em = discord.Embed(
                title="Quote",
                description=item.text,
            )

            if item.urls:
                for url in item.urls:
                    try:
                        em.set_image(url=url)
                    except:
                        pass
                    else:
                        break

            if item.author_id:
                author = discord.utils.get(ctx.guild.members, id=item.author_id)
                if author:
                    em.set_footer(
                        text=author
                    )

            if item.timestamp:
                em.timestamp = item.timestamp

            await ctx.send(embed=em)
