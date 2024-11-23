"""Client for connecting to brawl stars server"""
import os
import requests


class BrawlClient:
    API_TOKEN = os.environ.get("BRAWL_API_TOKEN")

    def get_player_info(self, player_tag: str):
        """Get player info from brawl api"""
        player_tag = player_tag.replace("#", "%")
        response = requests.get(
            url=f"https://api.brawlstars.com/v1/players/{player_tag}",
            headers={
                "Authorization": f"Bearer {self.API_TOKEN}"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()  # Parse the JSON response
            return data
        else:
            return None
