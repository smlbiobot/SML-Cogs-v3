from .sml import SML


async def setup(bot):
    bot.add_cog(SML(bot))
