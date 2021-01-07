from .autotranslate import AutoTranslate

def setup(bot):
    bot.add_cog(AutoTranslate(bot))