from .dstats import DStats

def setup(bot):
    bot.add_cog(DStats(bot))