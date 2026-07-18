import os
import pickle
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from discord import TextChannel

from brawl_client import BrawlClient
from message_controller import MessageController


class TestMessageController(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.target_channel = AsyncMock(spec=TextChannel)
        self.controller = MessageController(self.target_channel)
        self.controller.brawl_client = MagicMock(spec=BrawlClient)

    def test_initialization(self):
        self.assertEqual(self.controller.message_char_len_limit, 100)
        self.assertEqual(self.controller.name, "brawlbot")
        self.assertIn("profile", self.controller.available_commands)
        self.assertIn("catalog", self.controller.available_commands)
        self.assertIn("collection", self.controller.available_commands)
        self.assertIn("remove", self.controller.available_commands)
        self.assertEqual(self.controller.players_to_track, {})
        self.assertEqual(self.controller.player_map, {})
        self.assertEqual(self.controller.player_stats, {})
        self.assertEqual(self.controller.target_channel, self.target_channel)
        self.assertEqual(self.controller.version, "2.1.0")

    async def test_send_message(self):
        msg = "Hello, world!"
        await self.controller.send_message(msg)
        self.target_channel.send.assert_called_with(msg)

    async def test_send_help_message(self):
        await self.controller._send_help_message()
        self.target_channel.send.assert_called()
        help_text = self.target_channel.send.call_args[0][0]
        self.assertIn("profile", help_text)
        self.assertIn("catalog", help_text)

    async def test_send_status_message(self):
        self.controller.players_to_track = {"player1": {}}
        await self.controller._send_status_message()
        self.target_channel.send.assert_called_once()

    async def test_change_name(self):
        new_name = "new_brawlbot"
        await self.controller._change_name(new_name)
        self.assertEqual(self.controller.name, new_name)
        self.target_channel.send.assert_called_once_with(
            f"Changed bot name from brawlbot to {new_name}"
        )

    async def test_add_player(self):
        player_name = "player1"
        player_tag = "#12345"
        self.controller.brawl_client.get_player_info.return_value = {
            "trophies": 10500,
            "highestTrophies": 11000,
            "brawlers": [{"name": "SHELLY", "trophies": 500}],
        }
        await self.controller._add_player(player_name, player_tag)
        self.assertIn(player_name, self.controller.player_map)
        self.assertIn(player_name, self.controller.player_stats)
        stats = self.controller.player_stats[player_name]
        self.assertEqual(stats["last_trophies"], 10500)
        self.assertEqual(stats["last_highest_trophies"], 11000)
        # Seeded so we do not spam existing milestones
        self.assertIn(10000, stats["total_trophy_milestones"])
        self.assertEqual(stats["brawler_milestones"]["SHELLY"], [250, 500])
        self.target_channel.send.assert_called_once_with(
            f"Added player {player_name} with player tag {player_tag}"
        )

    async def test_start_tracking(self):
        self.controller.player_map = {"player1": "#12345"}
        self.controller.brawl_client.get_player_info.return_value = {
            "trophies": 100,
            "brawlers": [],
        }
        await self.controller._start_tracking("player1")
        self.assertIn("player1", self.controller.players_to_track)
        self.target_channel.send.assert_called_once()

    async def test_total_trophy_milestone_announcement(self):
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.player_stats = {
            "alice": {
                "tag": "#AAA",
                "total_trophy_milestones": [1000, 2000, 3000],
                "last_trophies": 3500,
                "last_highest_trophies": 3500,
                "brawler_milestones": {},
                "total_trophies_climbed": 0,
                "total_star_players": 0,
                "total_wins": 0,
                "total_defeats": 0,
            }
        }
        player_info = {"trophies": 4100, "highestTrophies": 4100, "brawlers": []}
        await self.controller._check_total_trophy_milestones("alice", player_info)
        sent = " ".join(call.args[0] for call in self.target_channel.send.call_args_list)
        self.assertIn("4,000", sent)
        self.assertIn(4000, self.controller.player_stats["alice"]["total_trophy_milestones"])

    async def test_peak_trophy_announcement(self):
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.player_stats = {
            "alice": {
                "tag": "#AAA",
                "total_trophy_milestones": [],
                "last_trophies": 5000,
                "last_highest_trophies": 5000,
                "brawler_milestones": {},
            }
        }
        player_info = {"trophies": 5050, "highestTrophies": 5050, "brawlers": []}
        await self.controller._check_peak_trophies("alice", player_info)
        sent = self.target_channel.send.call_args[0][0]
        self.assertIn("new peak", sent)
        self.assertEqual(self.controller.player_stats["alice"]["last_highest_trophies"], 5050)

    async def test_brawler_milestone_announcement(self):
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.player_stats = {
            "alice": {
                "tag": "#AAA",
                "brawler_milestones": {"SHELLY": [250]},
                "total_trophy_milestones": [],
                "last_trophies": 1000,
                "last_highest_trophies": 1000,
            }
        }
        player_info = {
            "trophies": 1000,
            "brawlers": [{"name": "SHELLY", "trophies": 500}],
        }
        await self.controller._check_milestones("alice", player_info)
        sent = self.target_channel.send.call_args[0][0]
        self.assertIn("SHELLY", sent)
        self.assertIn("500", sent)

    async def test_brawler_milestone_first_sight_silent(self):
        """First observation of a brawler seeds milestones without announcing."""
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.player_stats = {
            "alice": {
                "tag": "#AAA",
                "brawler_milestones": {},
                "total_trophy_milestones": [],
                "last_trophies": 1000,
                "last_highest_trophies": 1000,
            }
        }
        player_info = {
            "trophies": 1000,
            "brawlers": [{"name": "SHELLY", "trophies": 800}],
        }
        await self.controller._check_milestones("alice", player_info)
        self.target_channel.send.assert_not_called()
        self.assertEqual(
            self.controller.player_stats["alice"]["brawler_milestones"]["SHELLY"],
            [250, 500, 750],
        )

    async def test_monitor_registered_players(self):
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.player_stats = {
            "alice": {
                "tag": "#AAA",
                "total_trophy_milestones": list(range(1000, 5001, 1000)),
                "last_trophies": 5000,
                "last_highest_trophies": 5000,
                "brawler_milestones": {},
            }
        }
        self.controller.brawl_client.get_player_info.return_value = {
            "trophies": 5000,
            "highestTrophies": 5000,
            "brawlers": [],
        }
        with patch.object(self.controller, "save_state") as mock_save:
            infos = await self.controller._monitor_registered_players()
        self.assertIn("alice", infos)
        # No new milestones — no save
        mock_save.assert_not_called()

    async def test_catalog_list(self):
        self.controller.brawl_client.get_brawlers.return_value = [
            {"id": 1, "name": "SHELLY"},
            {"id": 2, "name": "NITA"},
        ]
        await self.controller._send_catalog()
        text = self.target_channel.send.call_args[0][0]
        self.assertIn("SHELLY", text)
        self.assertIn("NITA", text)
        self.assertIn("2 brawlers", text)

    async def test_catalog_detail(self):
        self.controller.brawl_client.get_brawlers.return_value = [
            {"id": 16000000, "name": "SHELLY"},
        ]
        self.controller.brawl_client.get_brawler.return_value = {
            "id": 16000000,
            "name": "SHELLY",
            "starPowers": [{"name": "Shell Shock"}],
            "gadgets": [{"name": "Fast Forward"}],
        }
        await self.controller._send_catalog("shelly")
        text = self.target_channel.send.call_args[0][0]
        self.assertIn("SHELLY", text)
        self.assertIn("Shell Shock", text)
        self.assertIn("Fast Forward", text)

    async def test_collection(self):
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.brawl_client.get_brawlers.return_value = [
            {"id": 1, "name": "SHELLY"},
            {"id": 2, "name": "NITA"},
            {"id": 3, "name": "COLT"},
        ]
        self.controller.brawl_client.get_player_info.return_value = {
            "brawlers": [
                {"name": "SHELLY", "power": 11, "trophies": 600},
                {"name": "NITA", "power": 9, "trophies": 400},
            ]
        }
        await self.controller._send_collection("alice")
        text = self.target_channel.send.call_args[0][0]
        self.assertIn("2/3", text)
        self.assertIn("COLT", text)

    async def test_profile_sends_card(self):
        self.controller.player_map = {"alice": "#AAA"}
        self.controller.player_stats = {
            "alice": self.controller._default_player_stats("#AAA", {"trophies": 1000})
        }
        self.controller.brawl_client.get_player_info.return_value = {
            "tag": "#AAA",
            "name": "AliceInGame",
            "trophies": 12000,
            "highestTrophies": 12500,
            "expLevel": 140,
            "3vs3Victories": 1000,
            "soloVictories": 50,
            "duoVictories": 40,
            "club": {"name": "Cool Club"},
            "brawlers": [
                {"name": "SHELLY", "trophies": 800, "power": 11},
                {"name": "NITA", "trophies": 700, "power": 10},
            ],
        }
        with patch("message_controller.generate_profile_card", return_value="profile_alice.png") as mock_card:
            with patch.object(self.controller, "send_file", new_callable=AsyncMock) as mock_file:
                await self.controller._send_profile("alice")
        mock_card.assert_called_once()
        mock_file.assert_called_once()
        text = self.target_channel.send.call_args[0][0]
        self.assertIn("Profile", text)
        self.assertIn("12,000", text)

    def test_brawler_trophy_deltas_by_id(self):
        start = {
            "brawlers": [
                {"id": 1, "name": "SHELLY", "trophies": 100},
                {"id": 2, "name": "NITA", "trophies": 200},
            ]
        }
        # Order swapped + new brawler should not break matching
        end = {
            "brawlers": [
                {"id": 2, "name": "NITA", "trophies": 210},
                {"id": 1, "name": "SHELLY", "trophies": 100},
                {"id": 3, "name": "COLT", "trophies": 50},
            ]
        }
        deltas = self.controller._brawler_trophy_deltas(start, end)
        self.assertEqual(deltas, [("NITA", 10)])

    def test_battle_result_showdown(self):
        self.assertEqual(self.controller._battle_result({"result": "victory"}), "victory")
        self.assertEqual(self.controller._battle_result({"rank": 1}), "victory")
        self.assertEqual(self.controller._battle_result({"rank": 5}), "defeat")
        self.assertIsNone(self.controller._battle_result({}))

    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.dump")
    def test_save_state(self, mock_pickle_dump, mock_open_file):
        self.controller.player_map = {"player1": "#12345"}
        self.controller.player_stats = {"player1": {"last_trophies": 100}}
        self.controller.save_state()

        mock_open_file.assert_called_once_with("message_controller_state.pkl", "wb")
        mock_pickle_dump.assert_called_once()
        _, args, _ = mock_pickle_dump.mock_calls[0]
        saved_state = args[0]
        self.assertEqual(saved_state["player_map"], {"player1": "#12345"})
        self.assertEqual(saved_state["player_stats"], {"player1": {"last_trophies": 100}})
        self.assertEqual(saved_state["name"], "brawlbot")

    @patch("builtins.open", new_callable=mock_open, read_data=pickle.dumps({
        "player_map": {"player1": "#12345"},
        "name": "brawlbot",
    }))
    @patch("os.path.exists", return_value=True)
    @patch("pickle.load")
    def test_load_state(self, mock_pickle_load, mock_os_path_exists, mock_open_file):
        mock_pickle_load.return_value = {
            "player_map": {"player1": "#12345"},
            "player_stats": {"player1": {"last_trophies": 100}},
            "name": "brawlbot",
        }

        self.controller.load_state()

        mock_open_file.assert_called_once_with("message_controller_state.pkl", "rb")
        mock_pickle_load.assert_called_once()
        self.assertEqual(self.controller.player_map, {"player1": "#12345"})
        self.assertEqual(self.controller.player_stats["player1"]["last_trophies"], 100)
        # Backfilled fields
        self.assertEqual(self.controller.player_stats["player1"]["total_trophy_milestones"], [])
        self.assertEqual(self.controller.player_stats["player1"]["last_highest_trophies"], 100)
        self.assertEqual(self.controller.name, "brawlbot")


class TestProfileCard(unittest.TestCase):
    def test_generate_profile_card(self):
        from profile_card import generate_profile_card

        path = "test_profile_card.png"
        try:
            out = generate_profile_card(
                {
                    "name": "TestPlayer",
                    "tag": "#TEST",
                    "trophies": 20000,
                    "highestTrophies": 21000,
                    "expLevel": 100,
                    "3vs3Victories": 500,
                    "soloVictories": 20,
                    "duoVictories": 30,
                    "club": {"name": "TestClub"},
                    "brawlers": [
                        {"name": "SHELLY", "trophies": 900, "power": 11},
                        {"name": "NITA", "trophies": 800, "power": 10},
                    ],
                },
                local_stats={
                    "total_trophies_climbed": 120,
                    "total_star_players": 3,
                    "total_wins": 10,
                    "total_defeats": 4,
                },
                display_name="tester",
                output_path=path,
            )
            self.assertEqual(out, path)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 1000)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
