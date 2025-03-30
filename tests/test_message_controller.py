import unittest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from discord import TextChannel
from brawl_client import BrawlClient
from message_controller import MessageController
import pickle


class TestMessageController(unittest.TestCase):
    def setUp(self):
        self.target_channel = AsyncMock(spec=TextChannel)
        self.controller = MessageController(self.target_channel)
        self.controller.brawl_client = MagicMock(spec=BrawlClient)

    def test_initialization(self):
        self.assertEqual(self.controller.message_char_len_limit, 100)
        self.assertEqual(self.controller.name, "brawlbot")
        self.assertEqual(self.controller.available_commands, [
            "!help", "!setname", "!status", "!debug", "start", "add", "end"
        ])
        self.assertEqual(self.controller.players_to_track, {})
        self.assertEqual(self.controller.player_map, {})
        self.assertEqual(self.controller.target_channel, self.target_channel)

    async def test_send_message(self):
        msg = "Hello, world!"
        await self.controller.send_message(msg)
        self.target_channel.send.assert_called_with(msg)

    async def test_send_help_message(self):
        await self.controller._send_help_message()
        self.target_channel.send.assert_called_once()  # Assuming there's only one call to send in the method

    async def test_send_status_message(self):
        self.controller.players_to_track = {"player1": {}}
        await self.controller._send_status_message()
        self.target_channel.send.assert_called_once()  # Assuming there's only one call to send in the method

    async def test_change_name(self):
        new_name = "new_brawlbot"
        await self.controller._change_name(new_name)
        self.assertEqual(self.controller.name, new_name)
        self.target_channel.send.assert_called_once_with(f"Changed bot name from brawlbot to {new_name}")

    async def test_add_player(self):
        player_name = "player1"
        player_tag = "#12345"
        self.controller.brawl_client.get_player_info.return_value = {"trophies": 100}
        await self.controller._add_player(player_name, player_tag)
        self.assertIn(player_name, self.controller.player_map)
        self.target_channel.send.assert_called_once_with(f"Added player {player_name} with player tag {player_tag}")

    async def test_start_tracking(self):
        self.controller.player_map = {"player1": "#12345"}
        self.controller.brawl_client.get_player_info.return_value = {"trophies": 100, "brawlers": []}
        await self.controller._start_tracking("player1")
        self.assertIn("player1", self.controller.players_to_track)
        self.target_channel.send.assert_called_once()  # Assuming there's only one call to send in the method

    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.dump")
    def test_save_state(self, mock_pickle_dump, mock_open_file):
        self.controller.player_map = {"player1": "#12345"}
        self.controller.save_state()

        mock_open_file.assert_called_once_with("message_controller_state.pkl", "wb")
        mock_pickle_dump.assert_called_once()
        _, args, _ = mock_pickle_dump.mock_calls[0]
        saved_state = args[0]
        self.assertEqual(saved_state["player_map"], {"player1": "#12345"})
        self.assertEqual(saved_state["name"], "brawlbot")

    @patch("builtins.open", new_callable=mock_open, read_data=pickle.dumps({
        "player_map": {"player1": "#12345"},
        "name": "brawlbot"
    }))
    @patch("os.path.exists", return_value=True)
    @patch("pickle.load")
    def test_load_state(self, mock_pickle_load, mock_os_path_exists, mock_open_file):
        mock_pickle_load.return_value = {
            "player_map": {"player1": "#12345"},
            "name": "brawlbot"
        }

        self.controller.load_state()

        mock_open_file.assert_called_once_with("message_controller_state.pkl", "rb")
        mock_pickle_load.assert_called_once()
        self.assertEqual(self.controller.player_map, {"player1": "#12345"})
        self.assertEqual(self.controller.name, "brawlbot")


if __name__ == "__main__":
    unittest.main()
