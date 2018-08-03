from .audit import Audit

def setup(bot):
    bot.add_cog(Audit(bot))