"""Handle I/O of messages to discord bot"""
import os
from discord_bot import DiscordBot

if __name__ == "__main__":
    bot_token = os.environ["BRAWL_DISCORD_BOT_TOKEN"]  # Replace with your bot's token
    channel_id = os.environ["BRAWL_DISCORD_BOT_CHANNEL_ID"]  # Replace with your target channel's ID

    # Create and run the bot
    bot = DiscordBot(token=bot_token, channel_id=channel_id)
    bot.run()
