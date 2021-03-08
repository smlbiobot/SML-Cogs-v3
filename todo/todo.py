import datetime as dt

import discord
from discord import TextChannel
from redbot.core import commands
from redbot.core import Config
from redbot.core.bot import Red

UNIQUE_ID = 202010292240


class Todo(commands.Cog):
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)
        default_global = {}
        self.config.register_global(**default_global)
        default_guild = {
            "task_channel_id": None,
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        Listen to reactions
        :param reaction:
        :param user:
        :return:
        """
        pass

    @commands.mod_or_permissions()
    @commands.group()
    async def todoset(self, ctx):
        """ToDo Settings"""
        pass

    @todoset.command(name="channel")
    async def todoset_channel(self, ctx, channel: TextChannel = None):
        """Set channel for tasks"""
        if channel is None:
            channel = ctx.message.channel

        await self.config.guild(ctx.guild).task_channel_id.set(channel.id)
        msg = await ctx.send(f"To-do channel set to {channel.mention}")
        await msg.delete(delay=5)

    @commands.mod_or_permissions()
    @commands.command(name="todo")
    async def todo(self, ctx, *, message):
        """
        Add a todo item
        """
        channel_id = await self.config.guild(ctx.guild).task_channel_id()
        channel = self.bot.get_channel(channel_id)

        if not channel:
            await ctx.send("Channel is not set, or does not exist")
            return

        em = discord.Embed(
            title=message,
            color=discord.Color.blue()
        )
        message = await channel.send(embed=em)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await message.add_reaction("🦋")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.event_type != 'REACTION_ADD':
            return

        # message has no channel
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        # invalid message
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        if not message:
            return

        # message not in a guild
        guild = message.guild
        if not guild:
            return

        # message is not in task channel
        if message.channel.id != await self.config.guild(guild).task_channel_id():
            return

        # message author is not self
        if message.author.id != self.bot.user.id:
            return

        # added by bot
        if payload.user_id == self.bot.user.id:
            return

        str_emoji = str(payload.emoji)

        # invalid emojis
        if str_emoji not in ["✅", "❌", "🦋"]:
            return

        em = message.embeds[0]
        new_embed = em.copy()

        color = None
        if str_emoji == '✅':
            color = discord.Color.green()
        elif str_emoji == '❌':
            color = discord.Color.red()
        elif str_emoji == '🦋':
            color = discord.Color.blue()

        # edit embed
        # new_embed.color = color
        # await message.edit(embed=new_embed)

        # delete it
        await message.delete()

        # add status update to channel so it will have new message
        em = discord.Embed(
            title=f'{str_emoji} {new_embed.title}',
            color=color,
            timestamp=dt.datetime.utcnow()
        )

        await channel.send(
            embed=em,
        )
