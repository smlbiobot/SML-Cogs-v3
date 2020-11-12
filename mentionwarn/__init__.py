from .mentionwarn import MentionWarn


def setup(bot):
    bot.add_cog(MentionWarn(bot))
