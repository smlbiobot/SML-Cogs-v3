from .nlp import NaturalLanguageProcessingCog

def setup(bot):
    bot.add_cog(NaturalLanguageProcessingCog(bot))