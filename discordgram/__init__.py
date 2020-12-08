from .dicsordgram import Discordgram

def setup(bot):
    cog = Discordgram(bot)
    bot.add_cog(cog)