from .punish import Punish


async def setup(bot):
    cog = Punish(bot)
    bot.add_cog(cog)
    await cog.initialize()

