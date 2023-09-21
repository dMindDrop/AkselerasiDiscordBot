try:
    from discord.ui import ActionRow
    print("ActionRow is available in this environment.")
except ImportError:
    print("ActionRow is not available in this environment.")
