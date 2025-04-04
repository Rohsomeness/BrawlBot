"""Translate message to actions"""
import datetime
import os
import pickle
from discord import TextChannel
from brawl_client import BrawlClient


class MessageController:
    """Process messages and perform actions"""
    def __init__(self, target_channel: TextChannel):
        self.message_char_len_limit = 100
        self.name = "brawlbot"
        self.available_commands = [
            "!help", "!setname", "!status", "!debug", "start", "add", "end"
        ]
        self.players_to_track: dict[str, dict] = {}
        self.player_map: dict[str, str] = {}
        self.player_battle_map: dict[str, dict] = {}
        self.brawl_client = BrawlClient()
        self.target_channel = target_channel
        self.start_time = None

    async def send_message(self, msg: str) -> None:
        """Send message to Discord server"""
        if not self.target_channel:
            raise ValueError("Target channel is not set.")
        print(msg)
        await self.target_channel.send(msg)

    async def _send_help_message(self) -> None:
        """Send help message"""
        command_descriptions = {
            "!help": "print out all commands",
            "!setname <bot_name>": "set activation <bot_name> of bot",
            f"!{self.name} status": "show status of bot",
            f"!{self.name} add <player_name> <brawlstars_tag>": "add a player to storage",
            f"!{self.name} remove <player_name>": "remove a player from storage",
            f"!{self.name} grind": "start tracking all added players",
            f"!{self.name} start <player names separated by spaces>": "start tracking all added players",
            f"!{self.name} progress": "show temporary progress of players",
            f"!{self.name} end": "end tracking and show stats",
            f"!{self.name} reset": "empty all currently tracked players",
            "!debug": "show full status of bot",
        }
        help_msg = "List of available commands: \n"
        for cmd, desc in command_descriptions.items():
            help_msg += f"\t{cmd} - {desc}\n"
        await self.send_message(help_msg)

    async def _send_status_message(self) -> None:
        """Send status message of bot"""
        status_msg = f"Bot name: {self.name}\n"
        status_msg += "Tracked players:\n"
        for player, _ in self.players_to_track:
            status_msg += f"\t{player}\n"

        await self.send_message(status_msg)

    async def _change_name(self, name) -> None:
        """Change activation name"""
        if self.name == name:
            return
        name_change_msg = f"Changed bot name from {self.name}"
        self.name = name
        await self.send_message(f"{name_change_msg} to {self.name}")

    async def _show_registered_players(self) -> None:
        registered_players_msg = "Registered players:\n"
        for player, tag in self.player_map:
            registered_players_msg += f"{player}: {tag}"
        await self.send_message(registered_players_msg)

    async def _add_player(self, player_name: str, player_tag: str):
        if self.brawl_client.get_player_info(player_tag) is None:
            await self.send_message(f"Unable to find player tag {player_tag}")
            return
        self.player_map[player_name] = player_tag
        await self.send_message(f"Added player {player_name} with player tag {player_tag}")

    async def _remove_player(self, player_name: str):
        if player_name in self.player_map:
            del self.player_map[player_name]
            if player_name in self.players_to_track:
                del self.players_to_track[player_name]
            await self.send_message(f"Player {player_name} removed")
        else:
            await self.send_message(f"Could not find player {player_name} to remove")

    async def _start_tracking(self, names_to_track: str):
        """
        Start tracking a game. Log:
        - Trophy difference
        - Players that are activated
        - Star players
        """
        start_tracking_msg = "Started tracking players:\n"
        names = names_to_track.split(" ")
        for name in names:
            if name not in self.player_map:
                await self.send_message(f"Player {name} is not registered")
                return
            player_info = self.brawl_client.get_player_info(self.player_map[name])
            self.players_to_track[name] = player_info
            self.player_battle_map[name] = {
                "battle_start_times": {},
                "star_players": 0,
                "game_durations_s": 0,
                "victories": 0,
                "defeats": 0,
            }
            start_tracking_msg += f"\tName: {name}, Start Trophies: {player_info['trophies']}\n"
        await self.send_message(start_tracking_msg)
        self.start_time = datetime.datetime.now(tz=datetime.timezone.utc)

    def update_battle_logs_periodically(self) -> None:
        for name, battle_map in self.player_battle_map:
            game_log = self.brawl_client.get_player_battle_logs(self.player_map[name])
            for game_info in game_log:
                if datetime.datetime.strptime(game_info["battleTime"], "%Y%m%dT%H%M%S.000Z") < self.start_time:
                    continue
                if game_info["battleTime"] in battle_map["battle_start_times"]:
                    continue
                battle_map["battle_start_times"].add(game_info["battleTime"])
                if game_info["battle"]["starPlayer"]["tag"] == self.player_map[name]:
                    battle_map["star_players"] += 1
                battle_map["game_durations_s"] += game_info["battle"]["duration"]
                battle_map["victories"] += 1 if game_info["battle"]["result"] == "vicory" else 0
                battle_map["defeats"] += 1 if game_info["battle"]["result"] == "defeat" else 0

    async def _show_progress(self):
        """Show intermediate progresss"""
        msg = "Progress\n"
        msg += "===== Battle Stats =====\n"
        self.update_battle_logs_periodically()
        for player, battle_map in self.player_battle_map:
            msg += f"{player}:\n"
            if battle_map["game_durations_s"] == 0:
                continue
            msg += f"\tGames: {len(battle_map['battle_start_times'])}\n"
            msg += f"\tVictories: {battle_map['victories']}\n"
            msg += f"\tDefeats: {battle_map['defeats']}\n"
            msg += f"\tStar Players: {battle_map['star_players']}\n"
            msg += f"\tGame Time: {battle_map['game_durations_s']}\n"

        msg += "===== Trophy Gains =====\n"
        for player, start_player_info in self.players_to_track.items():
            end_player_info = self.brawl_client.get_player_info(self.player_map[player])
            trophy_gain = end_player_info["trophies"] - start_player_info["trophies"]
            msg += (
                f"{player}: Total: {trophy_gain}, "
                f"TPS: {trophy_gain / (self.player_battle_map[player]['game_durations_s'] or 1)}\n"
            )
            for brawler_num in range(len(end_player_info["brawlers"])):
                start_trophies = start_player_info["brawlers"][brawler_num]["trophies"]
                end_trophies = end_player_info["brawlers"][brawler_num]["trophies"]
                if end_trophies != start_trophies:
                    brawler_name = end_player_info["brawlers"][brawler_num]["name"]
                    msg += f"\t{brawler_name}: {end_trophies - start_trophies}\n"
        await self.send_message(msg)

    async def _end_tracking(self):
        """End tracking of players"""
        msg = "Ended Tracking\n"
        msg += "===== Battle Stats =====\n"
        self.update_battle_logs_periodically()
        for player, battle_map in self.player_battle_map:
            msg += f"{player}:\n"
            if battle_map["game_durations_s"] == 0:
                continue
            msg += f"\tGames: {len(battle_map['battle_start_times'])}\n"
            msg += f"\tVictories: {battle_map['victories']}\n"
            msg += f"\tDefeats: {battle_map['defeats']}\n"
            msg += f"\tStar Players: {battle_map['star_players']}\n"
            msg += f"\tGame Time: {battle_map['game_durations_s']}\n"

        msg += "===== Trophy Gains =====\n"
        for player, start_player_info in self.players_to_track.items():
            end_player_info = self.brawl_client.get_player_info(self.player_map[player])
            trophy_gain = end_player_info["trophies"] - start_player_info["trophies"]
            msg += (
                f"{player}: Total: {trophy_gain}, "
                f"TPS: {trophy_gain / (self.player_battle_map[player]['game_durations_s'] or 1)}\n"
            )
            for brawler_num in range(len(end_player_info["brawlers"])):
                start_trophies = start_player_info["brawlers"][brawler_num]["trophies"]
                end_trophies = end_player_info["brawlers"][brawler_num]["trophies"]
                if end_trophies != start_trophies:
                    brawler_name = end_player_info["brawlers"][brawler_num]["name"]
                    msg += f"\t{brawler_name}: {end_trophies - start_trophies}\n"
        self.players_to_track = {}
        self.start_time = None
        self.player_battle_map = {}
        await self.send_message(msg)

    def _validate_message(self, msg: str) -> bool:
        """Some basic validation on messages before analyzing"""
        if 1 < len(msg) < self.message_char_len_limit:
            return True
        if msg.split(" ", 1)[0] in [self.name, "!setname", "!help", "!status", "!debug"]:
            return True
        if msg.split(" ", 2)[1] in self.available_commands:
            return True
        return False

    async def process_message(self, msg: str) -> None:  # noqa: C901 - allow complexity
        """Process the message and perform action"""
        if not self._validate_message(msg):
            return
        main_command = msg.split(" ", 1)[0]

        # One word commands
        if main_command == "!debug":
            await self.send_message(str(self))
        elif main_command == "!help":
            await self._send_help_message()
        elif main_command == "!status":
            await self._send_status_message()

        elif main_command == "!setname":
            full_command = msg.split(" ", 1)
            if len(full_command) != 2:
                return
            await self._change_name(full_command[-1])

        elif f"!{self.name}" in msg:
            action = msg.split(f"!{self.name} ")[-1]
            if "reset" in action:
                self.players_to_track = {}
                self.player_battle_map = {}
                self.start_time = None
                await self.send_message("Cleared all tracked players")
                return
            elif "grind" in action:
                if len(self.players_to_track) != 0:
                    await self.send_message("Already tracking games")
                    return
                else:
                    all_tracked_players = " ".join(self.player_map.keys())
                    await self._start_tracking(all_tracked_players)
                    return
            elif "start" in action:
                if len(self.players_to_track) != 0:
                    await self.send_message("Already tracking games")
                    return
                else:
                    await self._start_tracking(action.split("start ")[-1])
            elif "progress" in action:
                await self._show_progress()
                return
            elif "end" in action:
                if len(self.players_to_track) == 0:
                    await self.send_message("Currently not tracking any players")
                    return
                await self._end_tracking()

            elif "add" in action:
                name = action.split(" ", 2)[1]
                tag = action.split(" ", 2)[-1]
                await self._add_player(name, tag)

            elif "remove" in action:
                name = action.split(" ", 2)[1]
                await self._remove_player(name)

        else:
            return
        self.save_state()

    def save_state(self, filename="message_controller_state.pkl") -> None:
        """Save the state of the controller to a file."""
        with open(filename, "wb") as file:
            pickle.dump({
                "player_map": self.player_map,
                "name": self.name,
            }, file)
        print(f"State saved to {filename}")

    def load_state(self, filename="message_controller_state.pkl") -> None:
        """Load the state of the controller from a file."""
        if os.path.exists(filename):
            with open(filename, "rb") as file:
                state = pickle.load(file)
                self.player_map = state.get("player_map", {})
                self.name = state.get("name", "brawlbot")
            print(f"State loaded from {filename}")
        else:
            print(f"No saved state found at {filename}")

    def __str__(self) -> str:
        """Print all attributes of self except for players to track"""
        attributes = vars(self)
        return '\n'.join(f"{key}: {value}"
                         for key, value in attributes.items()
                         if key not in {"players_to_track", "player_battle_map", "message_char_len_limit"})
