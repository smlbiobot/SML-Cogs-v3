from .message_quote import MessageQuote

def setup(bot):
    bot.add_cog(MessageQuote(bot))