from .emoji_util import EmojiUtil

def setup(bot):
    bot.add_cog(EmojiUtil(bot))