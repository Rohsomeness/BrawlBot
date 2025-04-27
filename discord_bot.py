import asyncio
import discord
from message_controller import MessageController


class DiscordBot:
    """Handle making discord bot"""
    def __init__(self, token: str, channel_id: int):
        # Store bot token and target channel ID
        self.token = token
        self.channel_id = channel_id

        intents = discord.Intents.default()
        intents.message_content = True  # Enable message content intent

        self.client = discord.Client(intents=intents)  # Pass intents to the client
        self.message_controller = None

        # Set up events
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""
        print(f"Logged in as {self.client.user}")

        # Get the target channel
        target_channel = self.client.get_channel(self.channel_id)

        if isinstance(target_channel, discord.TextChannel):
            # Initialize the MessageController with the Discord client and target channel
            self.message_controller = MessageController(
                target_channel=target_channel
            )
            self.message_controller.load_state()
            print("MessageController is ready")

            self.client.loop.create_task(self.update_battle_logs_periodically())
        else:
            print(f"Could not find channel with ID {self.channel_id}")

    async def update_battle_logs_periodically(self):
        """Call update_battle_logs every 5 minutes."""
        while True:
            try:
                if self.message_controller:
                    await self.message_controller.update_battle_logs()
            except Exception as e:
                print(f"Error updating battle logs: {e}")
            await asyncio.sleep(120)  # 2 minutes

    async def on_message(self, message: discord.Message):
        """Called when a message is sent in a channel the bot has access to."""
        if message.author == self.client.user:
            return  # Ignore the bot's own messages

        if message.content.startswith("!"):
            await self.message_controller.process_message(message.content)

    def run(self):
        """Start the bot."""
        self.client.run(self.token)
