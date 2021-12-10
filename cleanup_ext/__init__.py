from .cleanup_ext import CleanupExt

def setup(bot):
    bot.add_cog(CleanupExt(bot))