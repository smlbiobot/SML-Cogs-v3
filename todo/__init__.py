from .todo import Todo

def setup(bot):
    bot.add_cog(Todo(bot))