"""Client for connecting to the Brawl Stars API."""
import os
from typing import Any, Optional
from urllib.parse import quote

import requests


class BrawlClient:
    """Thin wrapper around the official Brawl Stars HTTP API."""

    BASE_URL = "https://api.brawlstars.com/v1"
    API_TOKEN = os.environ.get("BRAWL_API_TOKEN")

    def __init__(self, api_token: Optional[str] = None, timeout: int = 10):
        if api_token is not None:
            self.API_TOKEN = api_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.API_TOKEN}"}

    @staticmethod
    def encode_tag(tag: str) -> str:
        """Normalize a player/club tag for use in API paths."""
        cleaned = tag.strip().upper()
        if not cleaned.startswith("#"):
            cleaned = f"#{cleaned}"
        return quote(cleaned, safe="")

    def _get(self, path: str) -> tuple[Optional[Any], Optional[int]]:
        """
        Perform a GET request.

        Returns (json_body, None) on success, or (None, status_code) on failure.
        """
        response = requests.get(
            url=f"{self.BASE_URL}{path}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        if response.status_code == 200:
            return response.json(), None
        return None, response.status_code

    def get_player_info(self, player_tag: str) -> Optional[dict]:
        """Get player info from the Brawl Stars API."""
        data, _status = self._get(f"/players/{self.encode_tag(player_tag)}")
        return data

    def get_player_battle_logs(self, player_tag: str):
        """
        Get battle log items for a player.

        Returns a list of battles on success (possibly empty).
        Returns an int HTTP status code on failure.
        """
        data, status = self._get(f"/players/{self.encode_tag(player_tag)}/battlelog")
        if data is not None:
            return data.get("items") or []
        return status

    def get_brawlers(self) -> Optional[list]:
        """Return the full brawler catalog, or None on failure."""
        data, _status = self._get("/brawlers")
        if data is None:
            return None
        return data.get("items") or []

    def get_brawler(self, brawler_id: int) -> Optional[dict]:
        """Return a single brawler by numeric ID, or None on failure."""
        data, _status = self._get(f"/brawlers/{brawler_id}")
        return data
