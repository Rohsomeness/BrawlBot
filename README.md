# BrawlBot

BrawlBot is a Discord bot designed to interact with the Brawl Stars API. It can track player progress, manage player data, and respond to various commands within a Discord server.

## Features
- **Track Player Progress**: Monitor Brawl Stars player stats including trophies, brawlers, and more.
- **Manage Players**: Add, remove, and display registered players.
- **Bot Commands**: Utilize various commands to interact with the bot, such as `!help`, `!setname`, `!status`, and more.

## Setup Instructions

### Prerequisites

- Python 3+, only tested on Python 3.11 and 3.13
- Discord Bot Token (Follow the [instructions below](#creating-a-discord-bot) to set up a Discord bot)
- Brawl Stars API Token (Follow the [instructions below](#using-the-brawl-stars-api) to get your token)

### Installation

1. **Clone the Repository**

   ```sh
   git clone https://github.com/rohsomeness/brawlbot.git
   cd brawlbot
   ```
2. **Install Dependencies**

   Use the provided `requirements.txt` to install the necessary Python packages:

   ```sh
   pip install -r requirements.txt
   ```
3. **Set Environment Variables**

   Set your Brawl Stars API token and Discord bot token as environment variables:

   ```sh
   export BRAWL_API_TOKEN=your_brawl_stars_api_token
   export BRAWL_DISCORD_BOT_TOKEN=your_discord_bot_token
   export BRAWL_DISCORD_BOT_CHANNEL_ID=your_discord_channel_id
   ```

### Running the Bot

To run the bot, if on Linux, use the following command:

```sh
make run
```

On Windows, use the following command:

```sh
python3 main.py
```

### Using the Brawl Stars API

1. **Sign Up and Get an API Token**

   - Visit the [Brawl Stars API website](https://developer.brawlstars.com/).
   - Sign up for an account and create a new API token.

2. **Configure the API Token**

   Set the API token as an environment variable as shown in the setup instructions.

### Creating a Discord Bot

1. **Create a Bot on Discord**

   - Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   - Create a new application and add a bot to it.

2. **Get the Bot Token**

   - Under the "Bot" section, click "Copy" to copy the bot token. This token will be used to authenticate the bot.

3. **Add the Bot to Your Server**

   - Under the "OAuth2" section, select "bot" in the scopes, and choose the appropriate permissions.
   - Copy the generated URL and open it in your browser to add the bot to your server.

4. **Configure the Bot Token**

   Set the bot token as an environment variable as shown in the setup instructions.

## Usage

Once the bot is running, you can use the following commands in your Discord server:

- `!help`: Display the list of available commands.
- `!setname <bot_name>`: Set the bot's name.
- `!status`: Show the current status of the bot.
- `!debug`: Display detailed information about the bot.
- `!brawlbot add <player_name> <brawlstars_tag>`: Add a player to the tracking list.
- `!brawlbot remove <player_name>`: Remove a player from the tracking list.
- `!brawlbot start`: Start tracking the listed players.
- `!brawlbot progress`: Show the progress of tracked players.
- `!brawlbot end`: End tracking and show the final stats.

## Contributing

Feel free to submit issues or pull requests. Contributions are welcome!

