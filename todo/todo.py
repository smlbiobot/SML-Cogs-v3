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
        :param message:
        :return:
        """
        channel_id = await self.config.guild(ctx.guild).task_channel_id()
        channel = self.bot.get_channel(channel_id)

        em = discord.Embed(
            title=message,
            color=discord.Color.blue()
        )
        message = await channel.send(channel, embed=em)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await message.add_reaction("🦋")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):

        message = reaction.message

        # message is not self
        if message.author.id != self.bot.user.id:
            return

        # message is not in task channel
        if message.channel.id != await self.config.guild(reaction.message.guild).task_channel_id():
            return

        # user is bot
        if user.bot:
            return

        # invalid emojis
        if reaction.emoji not in ["✅", "❌", "🦋"]:
            return

        em = message.embeds[0]
        new_embed = em.copy()
        if reaction.emoji == '✅':
            new_embed.color = discord.Color.green()
        elif reaction.emoji == '❌':
            new_embed.color = discord.Color.red()
        elif reaction.emoji == '🦋':
            new_embed.color = discord.Color.blue()

        await message.edit(embed=new_embed)

        # add status update to channel so it will have new message
        em = discord.Embed(
            title=f'{reaction.emoji} {new_embed.title}',
            color=new_embed.color
        )
        await reaction.message.channel.send(
            embed=em
        )
