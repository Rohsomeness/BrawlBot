# BrawlBot

BrawlBot is a Discord bot for Brawl Stars grind sessions. It tracks players via the official API, roasts/hypes streaks, posts graphs, keeps lifetime stats, and monitors trophy milestones in the background.

## Features

- **Session tracking**: Start/grind/progress/end with trophy deltas, TPH, and matplotlib graphs
- **Constant monitoring**: Polls every 2 minutes for registered players
- **Trophy congratulations**: Announces account total milestones (every 1k), new peaks, and per-brawler milestones
- **Player profiles**: Text summary + generated profile image card
- **Brawler catalog**: Full catalog browse, per-brawler gadgets/star powers, collection completeness
- **Persistent stats**: Wins, defeats, star players, trophies climbed, leaderboard
- **Auto session**: Auto-starts when trophies change; auto-ends after 10 minutes idle

## Setup Instructions

### Prerequisites

- Python 3+, only tested on Python 3.11 and 3.13
- Discord Bot Token (see [Creating a Discord Bot](#creating-a-discord-bot))
- Brawl Stars API Token (see [Using the Brawl Stars API](#using-the-brawl-stars-api))

### Installation

1. **Clone the Repository**

   ```sh
   git clone https://github.com/rohsomeness/brawlbot.git
   cd brawlbot
   ```

2. **Install Dependencies**

   ```sh
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**

   ```sh
   export BRAWL_API_TOKEN=your_brawl_stars_api_token
   export BRAWL_DISCORD_BOT_TOKEN=your_discord_bot_token
   export BRAWL_DISCORD_BOT_CHANNEL_ID=your_discord_channel_id
   ```

### Running the Bot

Linux/macOS:

```sh
make run
```

Windows:

```sh
python3 main.py
```

### Using the Brawl Stars API

1. Visit the [Brawl Stars API website](https://developer.brawlstars.com/).
2. Sign up and create an API token (remember to whitelist the server IP).
3. Set `BRAWL_API_TOKEN` as shown above.

### Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application and add a bot; copy the bot token.
3. Under OAuth2, select the `bot` scope and message permissions; invite the bot to your server.
4. Enable **Message Content Intent** under the Bot tab.
5. Set `BRAWL_DISCORD_BOT_TOKEN` and `BRAWL_DISCORD_BOT_CHANNEL_ID`.

## Usage

Once the bot is running:

### General

- `!help` — list commands
- `!setname <bot_name>` — change activation name (default `brawlbot`)
- `!status` — bot status
- `!debug` — full debug dump

### Players

- `!brawlbot add <player_name> <brawlstars_tag>` — register a player
- `!brawlbot remove <player_name>` — unregister a player
- `!brawlbot profile [player_name]` — profile text + image card
- `!brawlbot stats [player_name]` — persistent bot-tracked totals
- `!brawlbot leaderboard` — leaderboard by trophies climbed
- `!brawlbot milestones` — account + brawler milestone progress
- `!brawlbot collection [player_name]` — owned vs full catalog

### Catalog

- `!brawlbot catalog` — list all brawlers
- `!brawlbot catalog <brawler>` — gadgets and star powers
- `!brawlbot brawlers` — alias for catalog

### Sessions

- `!brawlbot grind` — start tracking all registered players
- `!brawlbot start <names…>` — start tracking selected players
- `!brawlbot progress` / `!brawlbot edge` — mid-session progress + graphs
- `!brawlbot end` / `!brawlbot cum` — end session, graphs, MVP shoutout
- `!brawlbot reset` — clear active session without a full recap

### Background monitoring

Every ~2 minutes the bot:

1. Fetches each registered player
2. Congratulates on new **total trophy** milestones (every 1,000 from 1k up)
3. Congratulates on new **all-time peaks**
4. Congratulates on **per-brawler** milestones (250 / 500 / 750 / 1000 / 1250 / 1500)
5. Auto-starts a session if trophies moved
6. While a session is active, ingests new battles and may roast/hype streaks
7. Auto-ends after 10 minutes with no new battles

## Development

```sh
make test
make lint
```

## Contributing

Feel free to submit issues or pull requests. Contributions are welcome!
