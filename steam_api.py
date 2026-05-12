###Polling from Steam API ######
import requests
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
import httpx
from typing import Optional
import asyncio

API_KEY = os.getenv('STEAM_API_KEY')
STEAM_USER_ID = os.getenv('STEAM_USER_ID')
BASE_URL = os.getenv('BASE_URL')

#---------------------------------------------------------------------------


class SteamGame(BaseModel):
    appid: int
    name: str = "Unknown Game"
    playtime_forever: int = 0          # minutes
 
 
class SteamAchievement(BaseModel):
    api_name: str = Field(alias="apiname")
    achieved: int                       # 1 = unlocked, 0 = locked
    unlock_time: int = Field(0, alias="unlocktime")# Unix timestamp (0 if locked)
 
    model_config = {"populate_by_name": True}
 
 
class GameAchievements(BaseModel):
    appid: int
    game_name: str
    achievements: list[SteamAchievement]

# ---------------------------------------------------------------------------


class SteamClient:
    """
    Async Steam Web API client.
 
    Parameters
    ----------
    api_key : str
        Your Steam Web API key (https://steamcommunity.com/dev/apikey).
    timeout : float
        HTTP timeout in seconds.
    """
 
    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
 
    async def close(self) -> None:
        await self._client.aclose()
 
    async def __aenter__(self) -> "SteamClient":
        return self
 
    async def __aexit__(self, *_) -> None:
        await self.close()
 
    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
 
    async def get_owned_games(self, steam_id: str) -> list[SteamGame]:
        """
        Return all games owned by *steam_id* that have playtime or
        achievement data.
 
        Raises
        ------
        ValueError
            If the profile is private or the Steam ID is invalid.
        httpx.HTTPStatusError
            On non-2xx HTTP responses.
        """
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json",
        }
        data = await self._get(
            "/IPlayerService/GetOwnedGames/v1/", params=params
        )
 
        response = data.get("response", {})
        if not response:
            raise ValueError(
                f"No data returned for Steam ID {steam_id}. "
                "The profile may be private."
            )
 
        games_raw = response.get("games", [])
        return [SteamGame(**g) for g in games_raw]
 
    async def get_achievements(
        self, steam_id: str, appid: int
    ) -> Optional[GameAchievements]:
        """
        Return all achievements for *appid* for the given *steam_id*.
 
        Returns ``None`` when:
          - the game has no achievement system, or
          - the user's stats are private for this game.
 
        Raises
        ------
        httpx.HTTPStatusError
            On non-2xx HTTP responses (except 400, which Steam uses for
            "no stats schema" – handled gracefully).
        """
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "appid": appid,
            "format": "json",
        }
 
        try:
            data = await self._get(
                "/ISteamUserStats/GetPlayerAchievements/v1/", params=params
            )
        except httpx.HTTPStatusError as exc:
            # Steam returns 400 when a game has no stats schema
            if exc.response.status_code == 400:
                return None
            raise
 
        player_stats = data.get("playerstats", {})
 
        # success == 0  → private / no data
        if not player_stats.get("success", False):
            return None
        game_name = player_stats.get("gameName", f"App {appid}")
        achievements_raw = player_stats.get("achievements", [])
        if not achievements_raw:
            return None
 
        achievements = [SteamAchievement(**a) for a in achievements_raw]
        game_name = player_stats.get("gameName", f"App {appid}")
 
        return GameAchievements(
            appid=appid,
            game_name=game_name,
            achievements=achievements,
        )
 
    async def get_all_achievements(
        self, steam_id: str, games: list[SteamGame]
    ) -> list[GameAchievements]:
        """
        Fetch achievements for every game in *games* concurrently.
 
        Games without an achievement system are silently skipped.
        """
        tasks = [self.get_achievements(steam_id, g.appid) for g in games]
        results = await asyncio.gather(*tasks, return_exceptions=True)
 
        out: list[GameAchievements] = []
        for game, result in zip(games, results):
            if isinstance(result, Exception):
                # Log and continue – one failing game shouldn't stop polling
                print(f"[steam_client] Warning: could not fetch achievements "
                      f"for appid={game.appid} ({game.name}): {result}")
                continue
            if result is not None:
                out.append(result)
 
        return out
 
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
 
    async def _get(self, path: str, params: dict) -> dict:
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()





