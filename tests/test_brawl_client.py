import unittest
from unittest.mock import patch, Mock
from brawl_client import BrawlClient


class TestBrawlClient(unittest.TestCase):
    def setUp(self):
        self.brawl_client = BrawlClient(api_token="test-token")

    def test_encode_tag(self):
        self.assertEqual(BrawlClient.encode_tag("#PLAYER123"), "%23PLAYER123")
        self.assertEqual(BrawlClient.encode_tag("player123"), "%23PLAYER123")

    @patch("brawl_client.requests.get")
    def test_get_player_info_success(self, mock_get):
        player_tag = "#PLAYER123"
        encoded_tag = "%23PLAYER123"

        mock_response = Mock()
        expected_json = {
            "tag": "#PLAYER123",
            "name": "PlayerName",
            "trophies": 5000,
        }
        mock_response.status_code = 200
        mock_response.json.return_value = expected_json
        mock_get.return_value = mock_response

        result = self.brawl_client.get_player_info(player_tag)

        self.assertIsNotNone(result)
        self.assertEqual(result["tag"], "#PLAYER123")
        self.assertEqual(result["name"], "PlayerName")
        self.assertEqual(result["trophies"], 5000)
        mock_get.assert_called_once_with(
            url=f"https://api.brawlstars.com/v1/players/{encoded_tag}",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

    @patch("brawl_client.requests.get")
    def test_get_player_info_not_found(self, mock_get):
        player_tag = "#UNKNOWN123"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.brawl_client.get_player_info(player_tag)

        self.assertIsNone(result)

    @patch("brawl_client.requests.get")
    def test_get_player_battle_logs_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"battleTime": "20250101T000000.000Z"}]}
        mock_get.return_value = mock_response

        result = self.brawl_client.get_player_battle_logs("#TAG")
        self.assertEqual(len(result), 1)

    @patch("brawl_client.requests.get")
    def test_get_player_battle_logs_empty_items(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = self.brawl_client.get_player_battle_logs("#TAG")
        self.assertEqual(result, [])

    @patch("brawl_client.requests.get")
    def test_get_player_battle_logs_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = self.brawl_client.get_player_battle_logs("#TAG")
        self.assertEqual(result, 403)

    @patch("brawl_client.requests.get")
    def test_get_brawlers(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": 16000000, "name": "SHELLY"}]
        }
        mock_get.return_value = mock_response

        result = self.brawl_client.get_brawlers()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "SHELLY")

    @patch("brawl_client.requests.get")
    def test_get_brawler(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 16000000, "name": "SHELLY", "gadgets": []}
        mock_get.return_value = mock_response

        result = self.brawl_client.get_brawler(16000000)
        self.assertEqual(result["name"], "SHELLY")
        mock_get.assert_called_once_with(
            url="https://api.brawlstars.com/v1/brawlers/16000000",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )


if __name__ == "__main__":
    unittest.main()
