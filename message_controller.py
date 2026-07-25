"""Translate message to actions"""
import datetime
import os
import pickle
import random
from typing import Optional

from discord import File, TextChannel
from matplotlib import pyplot as plt

from brawl_client import BrawlClient
from profile_card import generate_profile_card


class MessageController:
    """Process messages and perform actions"""

    # Account total trophy milestones (announced when crossed)
    TOTAL_TROPHY_STEP = 1000
    TOTAL_TROPHY_MIN = 1000
    # Per-brawler trophy milestones
    BRAWLER_MILESTONES = [250, 500, 750, 1000, 1250, 1500]

    def __init__(self, target_channel: TextChannel):
        self.message_char_len_limit = 100
        self.name = "brawlbot"
        self.available_commands = [
            "!help", "!setname", "!status", "!debug", "start", "add", "remove", "end",
            "grind", "progress", "edge", "reset", "stats", "leaderboard", "milestones",
            "profile", "catalog", "collection", "brawlers", "power",
        ]
        self.players_to_track: dict[str, dict] = {}
        self.player_map: dict[str, str] = {}
        self.player_stats: dict[str, dict] = {}
        self.player_battle_map: dict[str, dict] = {}
        self.brawl_client = BrawlClient()
        self.target_channel = target_channel
        self.start_time = None
        self.last_activity_time = None
        self.auto_end_timeout = datetime.timedelta(minutes=10)
        self.version = "2.3.0"
        self._brawler_catalog_cache: Optional[list] = None
        self._ending_session = False

    def _default_player_stats(self, player_tag: str = "", player_info: Optional[dict] = None) -> dict:
        player_info = player_info or {}
        trophies = int(player_info.get("trophies") or 0)
        highest = int(player_info.get("highestTrophies") or trophies)
        return {
            "tag": player_tag or player_info.get("tag", ""),
            "total_trophies_climbed": 0,
            "total_star_players": 0,
            "total_wins": 0,
            "total_defeats": 0,
            "brawler_milestones": self._seed_brawler_milestones(player_info),
            "total_trophy_milestones": self._total_milestones_for_trophies(trophies),
            "last_trophies": trophies,
            "last_highest_trophies": highest,
        }

    def _seed_brawler_milestones(self, player_info: dict) -> dict:
        seeded = {}
        for brawler in player_info.get("brawlers") or []:
            brawler_name = brawler.get("name")
            if not brawler_name:
                continue
            seeded[brawler_name] = self._milestones_for_trophies(int(brawler.get("trophies") or 0))
        return seeded

    def _ensure_player_stats(self, name: str, player_info: Optional[dict] = None) -> dict:
        tag = self.player_map.get(name, "")
        if name not in self.player_stats:
            self.player_stats[name] = self._default_player_stats(tag, player_info)
        else:
            stats = self.player_stats[name]
            stats.setdefault("tag", tag)
            stats.setdefault("total_trophies_climbed", 0)
            stats.setdefault("total_star_players", 0)
            stats.setdefault("total_wins", 0)
            stats.setdefault("total_defeats", 0)
            stats.setdefault("brawler_milestones", {})
            stats.setdefault("total_trophy_milestones", [])
            stats.setdefault("last_trophies", (player_info or {}).get("trophies", 0))
            stats.setdefault(
                "last_highest_trophies",
                (player_info or {}).get("highestTrophies", stats.get("last_trophies", 0)),
            )
        return self.player_stats[name]

    async def send_message(self, msg: str) -> None:
        """Send message to Discord server (chunks if over Discord's limit)."""
        if not self.target_channel:
            raise ValueError("Target channel is not set.")
        print(msg)
        # Discord hard limit is 2000 characters
        limit = 1900
        if len(msg) <= limit:
            await self.target_channel.send(msg)
            return
        chunks = []
        current = []
        current_len = 0
        for line in msg.split("\n"):
            extra = len(line) + (1 if current else 0)
            if current and current_len + extra > limit:
                chunks.append("\n".join(current))
                current = [line]
                current_len = len(line)
            else:
                current.append(line)
                current_len += extra
        if current:
            chunks.append("\n".join(current))
        for chunk in chunks:
            await self.target_channel.send(chunk)

    async def send_file(self, file_path: str, content: Optional[str] = None) -> None:
        """Send a file to Discord server"""
        if not self.target_channel:
            raise ValueError("Target channel is not set.")
        print(file_path)
        with open(file_path, "rb") as f:
            kwargs = {"file": File(f)}
            if content:
                kwargs["content"] = content
            await self.target_channel.send(**kwargs)

    async def _send_help_message(self) -> None:
        """Send help message"""
        command_descriptions = {
            "!help": "print out all commands",
            "!setname <bot_name>": "set activation <bot_name> of bot",
            f"!{self.name} status": "show status of bot",
            f"!{self.name} add <player_name> <brawlstars_tag>": "add a player to storage",
            f"!{self.name} remove <player_name>": "remove a player from storage",
            f"!{self.name} grind": "start tracking all registered players",
            f"!{self.name} start <player names separated by spaces>": "start tracking selected players",
            f"!{self.name} progress / edge": "show temporary progress of players",
            f"!{self.name} end / cum": "end tracking and show stats",
            f"!{self.name} reset": "empty all currently tracked players",
            f"!{self.name} stats <player_name>": "show persistent totals for a player",
            f"!{self.name} leaderboard": "show persistent total leaderboard",
            f"!{self.name} milestones": "short trophy milestone summary for registered players",
            f"!{self.name} profile [player_name]": "show player profile + image card",
            f"!{self.name} catalog [brawler]": "browse the brawler catalog",
            f"!{self.name} collection [player_name]": "compare owned brawlers vs catalog",
            f"!{self.name} power <player_name> <brawler>": "full brawler details (power, trophies, gears, gadgets, star powers)",
            "!debug": "show full status of bot",
        }
        help_msg = "List of available commands: \n"
        for cmd, desc in command_descriptions.items():
            help_msg += f"\t{cmd} - {desc}\n"
        await self.send_message(help_msg)

    async def _send_status_message(self) -> None:
        """Send status message of bot"""
        status_msg = f"Bot name: {self.name}\n"
        status_msg += f"Version: {self.version}\n"
        status_msg += f"Registered players: {len(self.player_map)}\n"
        status_msg += f"Session active: {'Yes' if self.start_time else 'No'}\n"
        status_msg += "Tracked players:\n"
        for player in self.players_to_track:
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
        for player, tag in self.player_map.items():
            registered_players_msg += f"{player}: {tag}\n"
        await self.send_message(registered_players_msg)

    async def _add_player(self, player_name: str, player_tag: str):
        player_info = self.brawl_client.get_player_info(player_tag)
        if player_info is None:
            await self.send_message(f"Unable to find player tag {player_tag}")
            return
        self.player_map[player_name] = player_tag
        # Seed milestones so we don't spam historical thresholds on first monitor tick
        self.player_stats[player_name] = self._default_player_stats(player_tag, player_info)
        await self.send_message(f"Added player {player_name} with player tag {player_tag}")

    async def _remove_player(self, player_name: str):
        if player_name in self.player_map:
            del self.player_map[player_name]
            if player_name in self.players_to_track:
                del self.players_to_track[player_name]
            if player_name in self.player_stats:
                del self.player_stats[player_name]
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
        names = [n for n in names_to_track.split(" ") if n]
        for name in names:
            if name not in self.player_map:
                await self.send_message(f"Player {name} is not registered")
                return
            player_info = self.brawl_client.get_player_info(self.player_map[name])
            if player_info is None:
                await self.send_message("Error connecting to brawl API, might need to reset IP address")
                return
            self.players_to_track[name] = player_info
            self.player_battle_map[name] = {
                "battle_start_times": set(),
                "star_players": 0,
                "game_durations_s": 0,
                "victories": 0,
                "defeats": 0,
                "consecutive_victories": 0,
                "consecutive_losses": 0,
            }
            self._ensure_player_stats(name, player_info)
            start_tracking_msg += f"\tName: {name}, Start Trophies: {player_info['trophies']}\n"
        await self.send_message(start_tracking_msg)
        self.start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        self.last_activity_time = self.start_time

    async def _auto_start_session(self, player_infos: Optional[dict] = None):
        if self.start_time is not None or not self.player_map:
            return
        names_to_track = []
        for name, tag in self.player_map.items():
            player_info = (player_infos or {}).get(name)
            if player_info is None:
                player_info = self.brawl_client.get_player_info(tag)
            if player_info is None:
                continue
            stats = self._ensure_player_stats(name, player_info)
            last_trophies = stats.get("last_trophies")
            if last_trophies is None or player_info["trophies"] != last_trophies:
                names_to_track.append(name)
                stats["last_trophies"] = player_info["trophies"]
        if names_to_track:
            await self._start_tracking(" ".join(names_to_track))
            await self.send_message("Auto-started a new tracking session based on recent player activity.")

    async def _auto_end_session(self):
        if self._ending_session or self.start_time is None or self.last_activity_time is None:
            return
        if datetime.datetime.now(tz=datetime.timezone.utc) - self.last_activity_time > self.auto_end_timeout:
            await self._end_tracking()

    def _milestones_for_trophies(self, trophies: int) -> list:
        return [threshold for threshold in self.BRAWLER_MILESTONES if trophies >= threshold]

    def _total_milestones_for_trophies(self, trophies: int) -> list:
        if trophies < self.TOTAL_TROPHY_MIN:
            return []
        return list(range(self.TOTAL_TROPHY_MIN, trophies + 1, self.TOTAL_TROPHY_STEP))

    async def _check_total_trophy_milestones(self, name: str, player_info: dict) -> bool:
        """Announce when account total trophies cross 1k steps. Returns True if anything announced."""
        stats = self._ensure_player_stats(name, player_info)
        trophies = int(player_info.get("trophies") or 0)
        current = set(self._total_milestones_for_trophies(trophies))
        previous = set(stats.get("total_trophy_milestones") or [])
        new_thresholds = sorted(current - previous)
        announced = False
        for milestone in new_thresholds:
            await self.send_message(
                f"🏆 **{name}** just hit **{milestone:,}** total trophies! (now at {trophies:,})"
            )
            announced = True
        stats["total_trophy_milestones"] = sorted(current)
        stats["last_trophies"] = trophies
        return announced

    async def _check_peak_trophies(self, name: str, player_info: dict) -> bool:
        """Announce new all-time trophy peaks."""
        stats = self._ensure_player_stats(name, player_info)
        highest = int(player_info.get("highestTrophies") or player_info.get("trophies") or 0)
        previous_peak = int(stats.get("last_highest_trophies") or 0)
        announced = False
        if previous_peak and highest > previous_peak:
            await self.send_message(
                f"🚀 **{name}** set a new peak: **{highest:,}** trophies "
                f"(was {previous_peak:,})!"
            )
            announced = True
        stats["last_highest_trophies"] = max(previous_peak, highest)
        return announced

    async def _check_milestones(self, name, player_info) -> bool:
        """Announce per-brawler trophy milestones. Returns True if anything announced."""
        stats = self._ensure_player_stats(name, player_info)
        announced = False
        for brawler in player_info.get("brawlers", []):
            brawler_name = brawler.get("name")
            if not brawler_name:
                continue
            current_thresholds = self._milestones_for_trophies(int(brawler.get("trophies") or 0))
            # First time we see this brawler: seed silently (avoids spam on unlock / state migration)
            if brawler_name not in stats["brawler_milestones"]:
                stats["brawler_milestones"][brawler_name] = current_thresholds
                continue
            previous_thresholds = set(stats["brawler_milestones"].get(brawler_name, []))
            new_thresholds = set(current_thresholds) - previous_thresholds
            if new_thresholds:
                for milestone in sorted(new_thresholds):
                    await self.send_message(
                        f"⭐ {name} just hit a milestone with {brawler_name}: {milestone} trophies!"
                    )
                    announced = True
                stats["brawler_milestones"][brawler_name] = sorted(
                    previous_thresholds.union(current_thresholds)
                )
        return announced

    async def _monitor_registered_players(self) -> dict:
        """
        Constant monitoring: fetch every registered player and announce
        total-trophy milestones, new peaks, and brawler milestones.
        Returns name -> player_info for reuse by auto-start.
        """
        player_infos = {}
        any_announcement = False
        for name, tag in list(self.player_map.items()):
            player_info = self.brawl_client.get_player_info(tag)
            if player_info is None:
                continue
            player_infos[name] = player_info
            total_hit = await self._check_total_trophy_milestones(name, player_info)
            peak_hit = await self._check_peak_trophies(name, player_info)
            brawler_hit = await self._check_milestones(name, player_info)
            if total_hit or peak_hit or brawler_hit:
                any_announcement = True
        if any_announcement:
            self.save_state()
        return player_infos

    async def _send_session_outcome_graph(self) -> None:
        plt.figure()
        plt.title("Session Outcomes")
        plt.xlabel("Player")
        plt.ylabel("Games")
        labels = list(self.player_battle_map.keys())
        wins = [self.player_battle_map[name]["victories"] for name in labels]
        defeats = [self.player_battle_map[name]["defeats"] for name in labels]
        x = range(len(labels))
        bar_width = 0.35
        plt.bar([xi - bar_width / 2 for xi in x], wins, width=bar_width, label="Wins", color="#4CAF50")
        plt.bar([xi + bar_width / 2 for xi in x], defeats, width=bar_width, label="Defeats", color="#F44336")
        plt.xticks(list(x), labels, rotation=45, ha="right")
        plt.legend()
        plt.subplots_adjust(bottom=0.2)
        filename = "session_outcomes.png"
        plt.savefig(filename)
        plt.close()
        await self.send_file(filename)

    async def berate_player(self, player_name, consecutive_victories, consecutive_losses):
        if consecutive_victories >= 5:
            congratulations_messages = [
                f"{player_name} is popping off, {consecutive_victories} wins in a row!",
                f"{player_name} just nutted on the randoms {consecutive_victories} times in a row!",
                f"{player_name} clapped cheeks {consecutive_victories} games straight — call that a hot streak!",
                f"{player_name} went full sweat mode and dommed {consecutive_victories} matches!",
                f"{player_name} raw-dogged the enemy team {consecutive_victories} times — zero protection!",
                f"{player_name} served {consecutive_victories} rounds of certified gamer pipe!",
                f"{player_name} smashed {consecutive_victories} teams so hard they’re filing a complaint!",
                f"{player_name} left no lube, no mercy — {consecutive_victories} straight wins!",
                f"{player_name} just turned {consecutive_victories} lobbies into their personal OnlyFans content!",
                f"{player_name} laid down the pipe {consecutive_victories} times like a horny builder in Power League!",
                f"{player_name} just raw-fucked {consecutive_victories} teams in a row—no lube, no mercy.",
                f"{player_name} nutted on the enemy spawn {consecutive_victories} times. The cleanup crew’s on strike.",
                f"{player_name} piped {consecutive_victories*3} randoms so hard they’re questioning their mains.",
                f"{player_name} went full step-bro mode and dominated {consecutive_victories} lobbies.",
                f"{player_name} had {consecutive_victories} straight wins and somehow got every enemy pregnant. Wipe up.",
                f"{player_name} violated {consecutive_victories} squads like a Terms of Service agreement.",
                f"{player_name} dropped {consecutive_victories} wins harder than OnlyFans leaks on Twitter.",
                f"{player_name} has been bending teams over {consecutive_victories} times in a row. At this point it’s a kink",
                f"{player_name} made {consecutive_victories} matches look like casting couch auditions.",
            ]
            await self.send_message(random.choice(congratulations_messages))
            return
        if consecutive_losses >= 3:
            roast_messages = [
                f"{player_name} just gave {consecutive_losses} teams the full Gawk Gawk 9000 with the gamer grip.",
                f"Yo {player_name} you are cheeks bro",
                f"{player_name} try to win a game challenge, impossible",
                f"Yo hop off {player_name}, today is not ur day",
                f"{consecutive_losses} is crazy work @{player_name}",
                f"{player_name} got folded like a lawn chair",
                f"{player_name} is out here playing for the other team fr",
                f"Someone bench {player_name} please",
                f"{player_name} is plays like old people fuck",
                f"Bro {player_name} forgot the objective was to win",
                f"{player_name} out here handing out free wins like it's Christmas",
                f"Call {player_name} a refund because they selling rn",
                f"{player_name} couldn't clutch a 1vNone",
                f"Give {player_name} some bots bruh",
                f"{player_name} getting packed up every round, consistently. {consecutive_losses} rounds to be precise",
                f"Yo {player_name}, you lost {consecutive_losses} in a row — blink twice if you need help",
                f"{player_name} making the enemy team look like Tensai",
                f"{player_name} getting humbled by bots",
                f"{player_name} built like a highlight reel for the enemy",
                f"{player_name} playing like they got inverted controls on",
                f"{player_name} losing streak: {consecutive_losses}. You're inventing new ways to lose bro",
                f"{player_name} couldn't hit water if they fell out a boat, {consecutive_losses} losses is crazy work",
                f"{player_name} try to hit the enemy challenge: impossible",
                f"Bro {player_name} getting cooked like a rotisserie chicken",
                f"{player_name} moving like a fridge out there",
                f"{player_name} out here donating trophies to the enemy",
                f"Sheesh {player_name}, maybe try using two hands",
                f"{player_name} might need to unplug and reflect",
                f"{player_name} needs a training montage ASAP",
                f"Someone get {player_name} a GPS — {consecutive_losses} games lost and still lost in the sauce",
                f"{player_name} got nerfed IRL",
                f"{player_name} turned lag into a playstyle",
                f"{player_name} couldn't carry groceries let alone a team",
                f"Not even AI would draft {player_name}",
                f"Put {player_name} in timeout bro",
                f"Yo {player_name} - ur probably playing against kids, why are you losing {consecutive_losses} in a row bro",
                f"{player_name} playing like the battery's at 2%",
                f"{player_name} needs to uninstall and meditate",
                f"Big L energy from {player_name} today",
                f"{player_name} couldn't save a file let alone a game",
                f"Retire, {player_name}, the streets are calling",
                f"{player_name} playing like a guest account",
                f"Bro {player_name} got a KD ratio of a potato",
                f"{player_name} couldn't aim at a barn from 3 feet away",
                f"{player_name} catching more Ls than a spelling bee",
                f"Congrats {player_name}, {consecutive_losses} losses. You’re the enemy MVP",
                f"{player_name} built like an error 404",
                f"{player_name} fighting for their life in bronze rank",
                f"{player_name} couldn't win a game with cheat codes",
                f"{player_name} playing like an unplugged router",
                f"{player_name} makes AFK players look useful",
                f"{player_name} couldn't win a rigged game",
                f"Yo {player_name}, that performance was criminal",
                f"{player_name} plays like they got patch notes nerfing their soul",
                f"{player_name} is the definition of deadweight",
                f"{player_name} getting humbled every lobby",
                f"{player_name} playing defense... for the enemy",
                f"{player_name} forgot they were supposed to win",
                f"{player_name} moving slower than patch updates",
                f"Legend says {player_name} is still respawning after {consecutive_losses} straight Ls",
                f"{player_name} thought the point was to lose as fast as possible",
                f"Bro {player_name} typing excuses faster than playing",
                f"{player_name} couldn't dodge a rock in open field",
                f"{player_name} playing with vision cones off",
                f"Put {player_name} on the bench and call it a buff",
                f"Yo {player_name} — load into the lobby, stay in spawn",
                f"{player_name} playing like they're on airplane mode",
                f"{player_name} has lost {consecutive_losses} games straight. This might be a world record",
                f"{player_name} losing 1v1s to NPCs programmed to lose",
                f"{player_name} needs a Rosetta Stone for basic mechanics",
                f"{player_name} pressing random buttons like it's Guitar Hero",
                f"{player_name} looking like the practice bot rn",
                f"Yo {player_name} have you considered dodging?",
                f"Bro {player_name} sit this next one out, {consecutive_losses} consecutive losses is crazy work",
                f"{player_name} just got dicked down {consecutive_losses} times in a row—no reacharound, no respawn.",
                f"{player_name} took {consecutive_losses} Ls back-to-back like they’re addicted to getting rawed.",
                f"{player_name} been bent over {consecutive_losses} times straight—someone hand 'em a towel and a therapist.",
                f"{player_name} got smashed harder than a Piper main in the wrong bush—{consecutive_losses} times!",
                f"{player_name} been used {consecutive_losses} times like a low-rank Tara in the back of a club.",
                f"{player_name} taking more punishment than a ball gagged Colt in overtime—{consecutive_losses} Ls deep.",
                f"{player_name} just gave up {consecutive_losses} wins like a Bibi at a frat party—wide open and no aim.",
                f"{player_name} been getting clapped so hard, {consecutive_losses} teams owe them child support.",
                f"{player_name} lost {consecutive_losses} games in a row—at this point it’s not matchmaking, it’s a gangbang.",
                f"{player_name} just got run through {consecutive_losses} times like a Tinder hookup in a Wi-Fi dead zone.",
            ]
            await self.send_message(random.choice(roast_messages))
        return

    def _battle_result(self, battle: dict) -> Optional[str]:
        """Normalize battle outcome; showdown uses rank instead of result."""
        if battle.get("result") in ("victory", "defeat", "draw"):
            return battle["result"]
        # Solo/duo showdown: rank 1 is a win for solo; rank <=2-ish for duo is messy — treat rank 1 as victory
        if "rank" in battle:
            rank = battle.get("rank")
            if rank == 1:
                return "victory"
            if rank is not None:
                return "defeat"
        return None

    async def _refresh_session_battles(self) -> bool:
        """Ingest new battle-log entries for the active session. Returns True if any activity."""
        if self.start_time is None:
            return False

        any_activity = False
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        for name, battle_map in self.player_battle_map.items():
            game_log = self.brawl_client.get_player_battle_logs(self.player_map[name])
            if isinstance(game_log, int):
                await self.send_message(
                    f"Error {game_log} with brawl API for updating battle logs, try sending message again"
                )
                return any_activity

            for game_info in game_log:
                battle_time = datetime.datetime.strptime(
                    game_info["battleTime"], "%Y%m%dT%H%M%S.000Z"
                ).replace(tzinfo=datetime.timezone.utc)
                if battle_time < self.start_time:
                    continue
                if game_info["battleTime"] in battle_map["battle_start_times"]:
                    continue

                any_activity = True
                battle_map["battle_start_times"].add(game_info["battleTime"])
                battle = game_info.get("battle") or {}
                if battle.get("starPlayer", {}).get("tag") == self.player_map[name]:
                    battle_map["star_players"] += 1
                    self._ensure_player_stats(name)
                    self.player_stats[name]["total_star_players"] = (
                        self.player_stats[name].get("total_star_players", 0) + 1
                    )
                trophy_change = battle.get("trophyChange", 0) or 0
                if trophy_change > 0:
                    self._ensure_player_stats(name)
                    self.player_stats[name]["total_trophies_climbed"] = (
                        self.player_stats[name].get("total_trophies_climbed", 0) + trophy_change
                    )
                if trophy_change != 0 and battle.get("duration") is not None:
                    battle_map["game_durations_s"] += battle["duration"]

                result = self._battle_result(battle)
                if result == "victory":
                    battle_map["victories"] += 1
                    battle_map["consecutive_victories"] += 1
                    battle_map["consecutive_losses"] = 0
                    self._ensure_player_stats(name)
                    self.player_stats[name]["total_wins"] = self.player_stats[name].get("total_wins", 0) + 1
                elif result == "defeat":
                    battle_map["defeats"] += 1
                    battle_map["consecutive_victories"] = 0
                    battle_map["consecutive_losses"] += 1
                    self._ensure_player_stats(name)
                    self.player_stats[name]["total_defeats"] = (
                        self.player_stats[name].get("total_defeats", 0) + 1
                    )

                await self.berate_player(
                    name,
                    battle_map["consecutive_victories"],
                    battle_map["consecutive_losses"],
                )

        if any_activity:
            self.last_activity_time = now
            self.save_state()
        return any_activity

    async def update_battle_logs(self) -> None:
        # Always monitor registered players for trophy / brawler milestones
        player_infos = await self._monitor_registered_players()

        if self.start_time is None:
            await self._auto_start_session(player_infos)
        if self.start_time is None:
            return

        await self._refresh_session_battles()
        await self._auto_end_session()

    async def _send_progress_graph(self) -> None:
        """Send progress graph for trophies over time"""
        plt.figure()
        plt.title("Total Trophies Over Time")
        plt.xlabel("Time")
        plt.ylabel("Trophies")

        for name in self.players_to_track:
            game_log = self.brawl_client.get_player_battle_logs(self.player_map[name])
            times = [self.start_time]
            trophies = [self.players_to_track[name]["trophies"]]
            star_players = [False]
            if isinstance(game_log, int):
                await self.send_message(
                    f"Error {game_log} with brawl API for updating battle logs, try sending message again"
                )
                return

            for game_info in sorted(game_log, key=lambda x: x["battleTime"]):
                battle_time = datetime.datetime.strptime(
                    game_info["battleTime"], "%Y%m%dT%H%M%S.000Z"
                ).replace(tzinfo=datetime.timezone.utc)
                if battle_time < self.start_time:
                    continue
                times.append(battle_time)
                trophies.append(trophies[-1] + (game_info["battle"].get("trophyChange") or 0))
                star_players.append(
                    game_info["battle"].get("starPlayer", {}).get("tag") == self.player_map[name]
                )

            if len(times) == 1:
                continue
            times.append(datetime.datetime.now(datetime.timezone.utc))
            trophies.append(trophies[-1])
            star_players.append(False)
            plt.plot(times, trophies, marker="*", markevery=star_players, label=name)
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.subplots_adjust(bottom=0.2)
        filename = "trophy_plot.png"
        plt.savefig(filename)
        plt.close()
        await self.send_file(filename)

    async def _send_trophy_delta_graph(self) -> None:
        """Send progress graph for trophies over time"""
        plt.figure()
        plt.title("Trophies Delta Over Time")
        plt.xlabel("Time")
        plt.ylabel("Trophies")

        for name in self.players_to_track:
            game_log = self.brawl_client.get_player_battle_logs(self.player_map[name])
            times = [self.start_time]
            trophies = [0]
            star_players = [False]
            if isinstance(game_log, int):
                await self.send_message(
                    f"Error {game_log} with brawl API for updating battle logs, try sending message again"
                )
                return

            for game_info in sorted(game_log, key=lambda x: x["battleTime"]):
                battle_time = datetime.datetime.strptime(
                    game_info["battleTime"], "%Y%m%dT%H%M%S.000Z"
                ).replace(tzinfo=datetime.timezone.utc)
                if battle_time < self.start_time:
                    continue
                times.append(battle_time)
                trophies.append(trophies[-1] + (game_info["battle"].get("trophyChange") or 0))
                star_players.append(
                    game_info["battle"].get("starPlayer", {}).get("tag") == self.player_map[name]
                )

            times.append(datetime.datetime.now(datetime.timezone.utc))
            trophies.append(trophies[-1])
            star_players.append(False)
            plt.plot(times, trophies, marker="*", markevery=star_players, label=name)
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.subplots_adjust(bottom=0.2)
        filename = "trophy_delta_plot.png"
        plt.savefig(filename)
        plt.close()
        await self.send_file(filename)

    def _brawler_trophy_deltas(self, start_player_info: dict, end_player_info: dict) -> list:
        """Diff brawler trophies by id/name instead of list index."""
        start_by_key = {}
        for brawler in start_player_info.get("brawlers") or []:
            key = brawler.get("id") or brawler.get("name")
            if key is not None:
                start_by_key[key] = brawler
        deltas = []
        for brawler in end_player_info.get("brawlers") or []:
            key = brawler.get("id") or brawler.get("name")
            if key is None or key not in start_by_key:
                continue
            start_t = int(start_by_key[key].get("trophies") or 0)
            end_t = int(brawler.get("trophies") or 0)
            if end_t != start_t:
                deltas.append((brawler.get("name") or str(key), end_t - start_t))
        deltas.sort(key=lambda x: abs(x[1]), reverse=True)
        return deltas

    async def _send_stats_message(self, player_name: str = None) -> None:
        if player_name:
            stats = self.player_stats.get(player_name)
            if not stats:
                await self.send_message(f"No stats available for {player_name}")
                return
            msg = f"Stats for {player_name}:\n"
            msg += f"\tTotal trophies climbed: {stats.get('total_trophies_climbed', 0)}\n"
            msg += f"\tTotal star players: {stats.get('total_star_players', 0)}\n"
            msg += f"\tTotal wins: {stats.get('total_wins', 0)}\n"
            msg += f"\tTotal defeats: {stats.get('total_defeats', 0)}\n"
            msg += f"\tLast trophies: {stats.get('last_trophies', 0)}\n"
            msg += f"\tPeak trophies: {stats.get('last_highest_trophies', 0)}\n"
            await self.send_message(msg)
            return

        msg = "Persistent player stats:\n"
        if not self.player_stats:
            msg += "\tNo players registered yet."
            await self.send_message(msg)
            return
        for name, stats in self.player_stats.items():
            msg += f"**{name}**: trophies climbed={stats.get('total_trophies_climbed', 0)}, "
            msg += f"star players={stats.get('total_star_players', 0)}, "
            msg += f"wins={stats.get('total_wins', 0)}, defeats={stats.get('total_defeats', 0)}\n"
        await self.send_message(msg)

    async def _send_leaderboard(self) -> None:
        if not self.player_stats:
            await self.send_message("No leaderboard available until players earn progress.")
            return
        leaderboard = sorted(
            self.player_stats.items(),
            key=lambda item: (
                item[1].get("total_trophies_climbed", 0),
                item[1].get("total_star_players", 0),
                item[1].get("total_wins", 0),
            ),
            reverse=True,
        )
        msg = "Leaderboard by trophies climbed:\n"
        for idx, (name, stats) in enumerate(leaderboard, start=1):
            msg += (
                f"{idx}. {name}: trophies climbed={stats.get('total_trophies_climbed', 0)}, "
                f"star players={stats.get('total_star_players', 0)}, "
                f"wins={stats.get('total_wins', 0)}\n"
            )
        await self.send_message(msg)

    def _next_total_trophy_milestone(self, trophies: int) -> Optional[int]:
        if trophies < self.TOTAL_TROPHY_MIN:
            return self.TOTAL_TROPHY_MIN
        next_m = ((trophies // self.TOTAL_TROPHY_STEP) + 1) * self.TOTAL_TROPHY_STEP
        return next_m

    def _brawler_milestone_counts(self, player_info: dict) -> dict[int, int]:
        """How many owned brawlers have reached each trophy threshold."""
        counts = {m: 0 for m in self.BRAWLER_MILESTONES}
        for brawler in player_info.get("brawlers") or []:
            trophies = int(brawler.get("trophies") or 0)
            for threshold in self.BRAWLER_MILESTONES:
                if trophies >= threshold:
                    counts[threshold] += 1
        return counts

    async def _send_milestones(self) -> None:
        """Compact milestone summary — account totals + brawler threshold counts only."""
        if not self.player_map:
            await self.send_message("No milestone progress available yet.")
            return
        msg = "**Milestones**\n"
        for name in self.player_map:
            player_info = self.brawl_client.get_player_info(self.player_map[name])
            if player_info is None:
                msg += f"**{name}**: unable to load\n"
                continue
            trophies = int(player_info.get("trophies") or 0)
            highest = int(player_info.get("highestTrophies") or trophies)
            next_total = self._next_total_trophy_milestone(trophies)
            counts = self._brawler_milestone_counts(player_info)
            # Only show thresholds where at least one brawler has hit them
            brawler_bits = [
                f"{threshold}+×{count}"
                for threshold, count in counts.items()
                if count > 0
            ]
            brawler_summary = ", ".join(brawler_bits) if brawler_bits else "none yet"
            msg += (
                f"**{name}**: {trophies:,} trophies (peak {highest:,}) "
                f"→ next {next_total:,}\n"
                f"\tBrawlers: {brawler_summary}\n"
            )
        await self.send_message(msg)

    async def _send_profile(self, player_name: Optional[str] = None) -> None:
        if not player_name:
            if len(self.player_map) == 1:
                player_name = next(iter(self.player_map))
            else:
                names = ", ".join(self.player_map.keys()) or "(none)"
                await self.send_message(
                    f"Usage: !{self.name} profile <player_name>\nRegistered: {names}"
                )
                return
        if player_name not in self.player_map:
            await self.send_message(f"Player {player_name} is not registered")
            return

        player_info = self.brawl_client.get_player_info(self.player_map[player_name])
        if player_info is None:
            await self.send_message(f"Unable to load profile for {player_name}")
            return

        stats = self._ensure_player_stats(player_name, player_info)
        club = player_info.get("club") or {}
        brawlers = player_info.get("brawlers") or []
        top = sorted(brawlers, key=lambda b: int(b.get("trophies") or 0), reverse=True)[:3]
        top_line = ", ".join(
            f"{b.get('name')} ({b.get('trophies')})" for b in top
        ) or "n/a"

        msg = (
            f"**Profile — {player_name}** ({player_info.get('name', '')} {player_info.get('tag', '')})\n"
            f"Trophies: {int(player_info.get('trophies') or 0):,} "
            f"(peak {int(player_info.get('highestTrophies') or 0):,})\n"
            f"Level: {player_info.get('expLevel', '?')}\n"
            f"3v3 / Solo / Duo wins: "
            f"{player_info.get('3vs3Victories', 0)} / "
            f"{player_info.get('soloVictories', 0)} / "
            f"{player_info.get('duoVictories', 0)}\n"
            f"Club: {club.get('name') or 'None'}\n"
            f"Brawlers owned: {len(brawlers)}\n"
            f"Top brawlers: {top_line}\n"
            f"Tracked: +{stats.get('total_trophies_climbed', 0)} trophies, "
            f"{stats.get('total_star_players', 0)} stars, "
            f"{stats.get('total_wins', 0)}W-{stats.get('total_defeats', 0)}L"
        )
        await self.send_message(msg)

        try:
            path = generate_profile_card(
                player_info,
                local_stats=stats,
                display_name=player_name,
                output_path=f"profile_{player_name}.png",
            )
            await self.send_file(path)
        except Exception as exc:
            await self.send_message(f"Could not generate profile card: {exc}")

    def _get_catalog(self) -> Optional[list]:
        if self._brawler_catalog_cache is None:
            self._brawler_catalog_cache = self.brawl_client.get_brawlers()
        return self._brawler_catalog_cache

    @staticmethod
    def _normalize_brawler_name(name: str) -> str:
        return "".join(ch for ch in name.lower() if ch.isalnum())

    def _find_catalog_brawler(self, query: str, catalog: list) -> Optional[dict]:
        needle = self._normalize_brawler_name(query)
        for brawler in catalog:
            if self._normalize_brawler_name(brawler.get("name") or "") == needle:
                return brawler
        # partial match
        matches = [
            b for b in catalog
            if needle in self._normalize_brawler_name(b.get("name") or "")
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    async def _send_catalog(self, query: Optional[str] = None) -> None:
        catalog = self._get_catalog()
        if catalog is None:
            await self.send_message("Unable to load brawler catalog from the API.")
            return

        if not query:
            names = sorted((b.get("name") or "?") for b in catalog)
            msg = f"**Brawler catalog** — {len(names)} brawlers\n"
            msg += ", ".join(names)
            msg += f"\n\nUse `!{self.name} catalog <brawler>` for gadgets & star powers."
            await self.send_message(msg)
            return

        brawler = self._find_catalog_brawler(query, catalog)
        if brawler is None:
            # try direct API by scanning ids if partial multi-match
            needle = self._normalize_brawler_name(query)
            partial = [
                b.get("name") for b in catalog
                if needle in self._normalize_brawler_name(b.get("name") or "")
            ]
            if partial:
                await self.send_message(
                    f"Multiple matches for '{query}': {', '.join(partial[:15])}"
                )
            else:
                await self.send_message(f"No brawler found matching '{query}'")
            return

        # Prefer full detail endpoint when available
        detail = self.brawl_client.get_brawler(int(brawler["id"])) if brawler.get("id") else None
        data = detail or brawler
        star_powers = data.get("starPowers") or []
        gadgets = data.get("gadgets") or []
        msg = f"**{data.get('name')}** (id {data.get('id')})\n"
        if star_powers:
            msg += "Star powers:\n"
            for sp in star_powers:
                msg += f"\t• {sp.get('name')}\n"
        else:
            msg += "Star powers: none listed\n"
        if gadgets:
            msg += "Gadgets:\n"
            for g in gadgets:
                msg += f"\t• {g.get('name')}\n"
        else:
            msg += "Gadgets: none listed\n"
        await self.send_message(msg)

    async def _send_collection(self, player_name: Optional[str] = None) -> None:
        if not player_name:
            if len(self.player_map) == 1:
                player_name = next(iter(self.player_map))
            else:
                names = ", ".join(self.player_map.keys()) or "(none)"
                await self.send_message(
                    f"Usage: !{self.name} collection <player_name>\nRegistered: {names}"
                )
                return
        if player_name not in self.player_map:
            await self.send_message(f"Player {player_name} is not registered")
            return

        catalog = self._get_catalog()
        player_info = self.brawl_client.get_player_info(self.player_map[player_name])
        if catalog is None or player_info is None:
            await self.send_message("Unable to load collection data from the API.")
            return

        owned = {self._normalize_brawler_name(b.get("name") or ""): b for b in (player_info.get("brawlers") or [])}
        catalog_names = [(b.get("name") or "?", self._normalize_brawler_name(b.get("name") or "")) for b in catalog]
        missing = [name for name, key in catalog_names if key and key not in owned]
        owned_count = len(owned)
        total = len(catalog)

        # Power summary for owned
        max_power = sum(1 for b in owned.values() if int(b.get("power") or 0) >= 11)
        msg = (
            f"**Collection — {player_name}**\n"
            f"Owned: {owned_count}/{total} "
            f"({(100 * owned_count / total) if total else 0:.0f}%)\n"
            f"Power 11+: {max_power}\n"
        )
        if missing:
            show = missing[:30]
            msg += f"Missing ({len(missing)}): {', '.join(show)}"
            if len(missing) > 30:
                msg += f", … +{len(missing) - 30} more"
        else:
            msg += "Missing: none — full catalog!"
        await self.send_message(msg)

    def _find_owned_brawler(self, query: str, owned: list) -> Optional[dict]:
        """Find a brawler in a player's owned list by name (exact, then unique partial)."""
        needle = self._normalize_brawler_name(query)
        if not needle:
            return None
        for brawler in owned:
            if self._normalize_brawler_name(brawler.get("name") or "") == needle:
                return brawler
        matches = [
            b for b in owned
            if needle in self._normalize_brawler_name(b.get("name") or "")
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    async def _send_brawler_power(
        self,
        player_name: Optional[str] = None,
        brawler_query: Optional[str] = None,
    ) -> None:
        """Show power level (and related stats) for a player's brawler."""
        usage = (
            f"Usage: `!{self.name} power <player_name> <brawler>`\n"
            f"Example: `!{self.name} power alice shelly`"
        )
        # Single-arg form: treat as brawler when only one player is registered
        if player_name and not brawler_query:
            if len(self.player_map) == 1:
                brawler_query = player_name
                player_name = next(iter(self.player_map))
            else:
                names = ", ".join(self.player_map.keys()) or "(none)"
                await self.send_message(f"{usage}\nRegistered: {names}")
                return

        if not player_name or not brawler_query:
            names = ", ".join(self.player_map.keys()) or "(none)"
            await self.send_message(f"{usage}\nRegistered: {names}")
            return

        if player_name not in self.player_map:
            await self.send_message(f"Player {player_name} is not registered")
            return

        player_info = self.brawl_client.get_player_info(self.player_map[player_name])
        if player_info is None:
            await self.send_message(f"Unable to load data for {player_name}")
            return

        owned = player_info.get("brawlers") or []
        brawler = self._find_owned_brawler(brawler_query, owned)
        if brawler is None:
            needle = self._normalize_brawler_name(brawler_query)
            partial = [
                b.get("name") for b in owned
                if needle in self._normalize_brawler_name(b.get("name") or "")
            ]
            if partial:
                await self.send_message(
                    f"Multiple matches for '{brawler_query}': {', '.join(partial[:15])}"
                )
            else:
                # Clarify not-owned vs not-found in catalog
                catalog = self._get_catalog()
                in_catalog = (
                    catalog is not None
                    and self._find_catalog_brawler(brawler_query, catalog) is not None
                )
                if in_catalog:
                    await self.send_message(
                        f"**{player_name}** does not own **{brawler_query}** "
                        f"(or the name did not match uniquely)."
                    )
                else:
                    await self.send_message(
                        f"No brawler found matching '{brawler_query}' for {player_name}"
                    )
            return

        name = brawler.get("name") or brawler_query
        power = int(brawler.get("power") or 0)
        trophies = int(brawler.get("trophies") or 0)
        highest = int(brawler.get("highestTrophies") or trophies)
        rank = brawler.get("rank")
        gadgets = brawler.get("gadgets") or []
        star_powers = brawler.get("starPowers") or []
        gears = brawler.get("gears") or []

        msg = (
            f"**{player_name}** — **{name}**\n"
            f"Power: **{power}**\n"
            f"Trophies: {trophies:,} (peak {highest:,})\n"
        )
        if rank is not None:
            msg += f"Rank: {rank}\n"
        if brawler.get("id") is not None:
            msg += f"ID: {brawler.get('id')}\n"

        msg += "\n**Gadgets**\n"
        if gadgets:
            for g in gadgets:
                msg += f"\t• {g.get('name') or '?'}\n"
        else:
            msg += "\tnone\n"

        msg += "**Star powers**\n"
        if star_powers:
            for sp in star_powers:
                msg += f"\t• {sp.get('name') or '?'}\n"
        else:
            msg += "\tnone\n"

        msg += "**Gears**\n"
        if gears:
            for g in gears:
                gname = g.get("name") or "?"
                level = g.get("level")
                if level is not None:
                    msg += f"\t• {gname} (level {level})\n"
                else:
                    msg += f"\t• {gname}\n"
        else:
            msg += "\tnone\n"

        await self.send_message(msg)

    async def _show_progress(self):
        """Show intermediate progress"""
        msg = "Progress\n"
        msg += "===== Battle Stats =====\n"
        await self.update_battle_logs()
        for player, battle_map in self.player_battle_map.items():
            msg += f"**{player}**:\n"
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
            if end_player_info is None:
                msg += f"**{player}**: unable to fetch current trophies\n"
                continue
            trophy_gain = end_player_info["trophies"] - start_player_info["trophies"]
            trophy_per_hour = round(
                trophy_gain * 3600 / (self.player_battle_map[player]["game_durations_s"] or 1),
                2,
            )
            msg += (
                f"**{player}**: Total: {trophy_gain}, "
                f"TPH: {trophy_per_hour}\n"
            )
            for brawler_name, delta in self._brawler_trophy_deltas(start_player_info, end_player_info):
                msg += f"\t{brawler_name}: {delta:+d}\n"
        await self.send_message(msg)
        await self._send_trophy_delta_graph()
        await self._send_session_outcome_graph()

    async def _end_tracking(self):
        """End tracking of players"""
        if self._ending_session:
            return
        self._ending_session = True
        try:
            msg = "Ended Tracking\n"
            msg += "===== Battle Stats =====\n"
            most_star_players = ("nobody", 0)
            # Refresh battle stats without re-entering auto-end
            start_time = self.start_time
            if start_time is not None:
                await self._refresh_session_battles()
            for player, battle_map in self.player_battle_map.items():
                msg += f"**{player}**:\n"
                if battle_map["game_durations_s"] == 0:
                    continue
                msg += f"\tGames: {len(battle_map['battle_start_times'])}\n"
                msg += f"\tVictories: {battle_map['victories']}\n"
                msg += f"\tDefeats: {battle_map['defeats']}\n"
                msg += f"\tStar Players: {battle_map['star_players']}\n"
                msg += f"\tGame Time: {battle_map['game_durations_s']}\n"
                if battle_map["star_players"] > most_star_players[1]:
                    most_star_players = (player, battle_map["star_players"])

            msg += "===== Trophy Gains =====\n"
            for player, start_player_info in self.players_to_track.items():
                end_player_info = self.brawl_client.get_player_info(self.player_map[player])
                if end_player_info is None:
                    msg += f"**{player}**: unable to fetch current trophies\n"
                    continue
                trophy_gain = end_player_info["trophies"] - start_player_info["trophies"]
                trophy_per_hour = round(
                    trophy_gain * 3600 / (self.player_battle_map[player]["game_durations_s"] or 1),
                    2,
                )
                msg += (
                    f"**{player}**: Total: {trophy_gain}, "
                    f"TPH: {trophy_per_hour}\n"
                )
                for brawler_name, delta in self._brawler_trophy_deltas(start_player_info, end_player_info):
                    msg += f"\t{brawler_name}: {delta:+d}\n"
            await self.send_message(msg)
            await self._send_trophy_delta_graph()
            await self._send_session_outcome_graph()
            await self._send_progress_graph()
            await self.send_message(
                f"Congrats to {most_star_players[0]} for carrying the session "
                f"with {most_star_players[1]} star players!"
            )
            for player in list(self.players_to_track):
                final_info = self.brawl_client.get_player_info(self.player_map[player])
                if final_info is not None:
                    stats = self._ensure_player_stats(player, final_info)
                    stats["last_trophies"] = final_info.get("trophies", stats.get("last_trophies", 0))
                    await self._check_total_trophy_milestones(player, final_info)
                    await self._check_peak_trophies(player, final_info)
                    await self._check_milestones(player, final_info)
            self.players_to_track = {}
            self.start_time = None
            self.player_battle_map = {}
            self.save_state()
        finally:
            self._ending_session = False

    def _validate_message(self, msg: str) -> bool:
        """Some basic validation on messages before analyzing"""
        if 1 < len(msg) < self.message_char_len_limit:
            return True
        if msg.split(" ", 1)[0] in [self.name, "!setname", "!help", "!status", "!debug"]:
            return True
        parts = msg.split(" ", 2)
        if len(parts) >= 2 and parts[1] in self.available_commands:
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
            elif action == "grind" or action.startswith("grind "):
                if len(self.players_to_track) != 0:
                    await self.send_message("Already tracking games")
                    return
                all_tracked_players = " ".join(self.player_map.keys())
                await self._start_tracking(all_tracked_players)
                return
            elif action.startswith("start"):
                if len(self.players_to_track) != 0:
                    await self.send_message("Already tracking games")
                    return
                await self._start_tracking(action.split("start ")[-1] if "start " in action else "")
            elif action.startswith("progress") or action.startswith("edge"):
                if len(self.players_to_track) == 0:
                    await self.send_message("Currently not tracking any players")
                    return
                await self._show_progress()
                return
            elif action.startswith("end") or action.startswith("cum"):
                if len(self.players_to_track) == 0:
                    await self.send_message("Currently not tracking any players")
                    return
                await self._end_tracking()

            elif action.startswith("stats"):
                parts = action.split()
                if len(parts) >= 2:
                    await self._send_stats_message(parts[1])
                else:
                    await self._send_stats_message()
                return

            elif action.startswith("leaderboard"):
                await self._send_leaderboard()
                return

            elif action.startswith("milestones"):
                await self._send_milestones()
                return

            elif action.startswith("profile"):
                parts = action.split(maxsplit=1)
                await self._send_profile(parts[1].strip() if len(parts) > 1 else None)
                return

            elif action.startswith("catalog") or action.startswith("brawlers"):
                parts = action.split(maxsplit=1)
                await self._send_catalog(parts[1].strip() if len(parts) > 1 else None)
                return

            elif action.startswith("collection"):
                parts = action.split(maxsplit=1)
                await self._send_collection(parts[1].strip() if len(parts) > 1 else None)
                return

            elif action.startswith("power"):
                parts = action.split()
                if len(parts) < 2:
                    await self._send_brawler_power()
                elif len(parts) == 2:
                    # power <brawler> when only one registered player
                    await self._send_brawler_power(parts[1], None)
                else:
                    await self._send_brawler_power(parts[1], " ".join(parts[2:]))
                return

            elif action.startswith("add "):
                parts = action.split(" ", 2)
                if len(parts) < 3:
                    await self.send_message(f"Usage: !{self.name} add <player_name> <tag>")
                    return
                await self._add_player(parts[1], parts[2])

            elif action.startswith("remove "):
                parts = action.split(" ", 1)
                if len(parts) < 2:
                    await self.send_message(f"Usage: !{self.name} remove <player_name>")
                    return
                await self._remove_player(parts[1].strip())

        else:
            return
        self.save_state()

    def save_state(self, filename="message_controller_state.pkl") -> None:
        """Save the state of the controller to a file."""
        with open(filename, "wb") as file:
            pickle.dump({
                "player_map": self.player_map,
                "player_stats": self.player_stats,
                "name": self.name,
            }, file)
        print(f"State saved to {filename}")

    def load_state(self, filename="message_controller_state.pkl") -> None:
        """Load the state of the controller from a file."""
        if os.path.exists(filename):
            with open(filename, "rb") as file:
                state = pickle.load(file)
                self.player_map = state.get("player_map", {})
                self.player_stats = state.get("player_stats", {})
                self.name = state.get("name", "brawlbot")
                # Backfill new fields for older saved state without spamming historical milestones
                for name, stats in self.player_stats.items():
                    last_trophies = int(stats.get("last_trophies") or 0)
                    if "total_trophy_milestones" not in stats or stats["total_trophy_milestones"] is None:
                        stats["total_trophy_milestones"] = self._total_milestones_for_trophies(last_trophies)
                    stats.setdefault(
                        "last_highest_trophies",
                        int(stats.get("last_highest_trophies") or last_trophies),
                    )
                    stats.setdefault("brawler_milestones", {})
            print(f"State loaded from {filename}")
        else:
            print(f"No saved state found at {filename}")

    def __str__(self) -> str:
        """Print all attributes of self except for players to track"""
        attributes = vars(self)
        return "\n".join(
            f"{key}: {value}"
            for key, value in attributes.items()
            if key not in {
                "players_to_track",
                "player_battle_map",
                "message_char_len_limit",
                "_brawler_catalog_cache",
            }
        )
