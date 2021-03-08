from .timer import Timer


async def setup(bot):
    cog = Timer(bot)
    bot.add_cog(cog)


