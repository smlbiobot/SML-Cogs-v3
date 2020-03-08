def get_emoji(bot, name, remove_dash=True):
    """Return emoji by name

    name is used by this cog.
    key is values returned by the api.
    Use key only if name is not set
    """

    if remove_dash:
        name = name.replace('-', '')

    for guild in bot.guilds:
        for emoji in guild.emojis:
            if emoji.name == name:
                return f'<:{emoji.name}:{emoji.id}>'
    return f':{name}:'