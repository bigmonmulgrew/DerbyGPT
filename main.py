# main.py
import utils
import discord_bot

# Enable or disable debug mode based on your needs
utils.set_debug_mode(True)
utils.debug("Debugging mode enabled")

# Run the bot
discord_bot.run_bot()