import unittest
from unittest.mock import patch, Mock
from brawl_client import BrawlClient


class TestBrawlClient(unittest.TestCase):
    def setUp(self):
        self.brawl_client = BrawlClient()

    @patch('brawl_client.requests.get')
    def test_get_player_info_success(self, mock_get):
        player_tag = "#PLAYER123"
        encoded_tag = "%23PLAYER123"

        mock_response = Mock()
        expected_json = {
            "tag": "#PLAYER123",
            "name": "PlayerName",
            "trophies": 5000
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
            headers={"Authorization": f"Bearer {self.brawl_client.API_TOKEN}"},
            timeout=10
        )

    @patch('brawl_client.requests.get')
    def test_get_player_info_not_found(self, mock_get):
        player_tag = "#UNKNOWN123"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.brawl_client.get_player_info(player_tag)

        self.assertIsNone(result)
        mock_get.assert_called_once_with
