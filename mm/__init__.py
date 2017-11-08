from .mm import MemberManagement

def setup(bot):
    bot.add_cog(MemberManagement(bot))