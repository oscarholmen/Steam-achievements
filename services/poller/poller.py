"""
poller.py
---------
Henter achievements fra Steam, sammenligner med databasen,
og sender webhook-varsler når nye achievements låses opp.
 
Flyt:
  poll_user()
    ├── steam_client.get_owned_games()
    ├── steam_client.get_all_achievements()
    ├── upsert_games()
    ├── for hvert spill:
    │     ├── get_existing_achievements()  ← fra DB
    │     ├── diff()                       ← finn nye unlocks
    │     ├── upsert_achievements()        ← lagre i DB
    │     └── dispatch_webhooks()          ← varsle hvis noe nytt
    └── ferdig
"""
import asyncio
import os
from datetime import datetime
 
import httpx
import requests
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
 
from database import Achievement, SessionLocal, Game, Webhook, init_db
from steam_api import GameAchievements, SteamClient
from webhooks import send_webhook
 
load_dotenv()
 
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
STEAM_USER_ID = os.getenv("STEAM_USER_ID")
WEBHOOK_TIMEOUT = 5.0  # sekunder før webhook-kall gir opp

# ---------------------------------------------------------------------------
# Database-operasjoner
# ---------------------------------------------------------------------------
 
async def upsert_games(steam_id: str, games: list) -> None:
    """Lagrer eller oppdaterer spill i DB."""
    rows = [
        {
            "steam_id": steam_id,
            "appid": g.appid,
            "name": g.name,
            "playtime_forever": g.playtime_forever,
        }
        for g in games
    ]
    async with SessionLocal() as session:
        stmt = pg_insert(Game).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["steam_id", "appid"],
            set_={
                "name": stmt.excluded.name,
                "playtime_forever": stmt.excluded.playtime_forever,
            },
        )
        await session.execute(stmt)
        await session.commit()
 
 
async def get_existing_achievements(steam_id: str, appid: int) -> set[str]:
    """
    Returnerer et set med api_name for alle achievements som allerede
    er markert som achieved i databasen for dette spillet.
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(Achievement.api_name).where(
                Achievement.steam_id == steam_id,
                Achievement.appid == appid,
                Achievement.achieved == True,
            )
        )
        return {row[0] for row in result.fetchall()}
 
 
async def upsert_achievements(steam_id: str, game: GameAchievements) -> None:
    """Lagrer eller oppdaterer alle achievements for ett spill."""
    rows = [
        {
            "steam_id": steam_id,
            "appid": game.appid,
            "api_name": a.api_name,
            "achieved": a.achieved == 1,
            "unlock_time": a.unlock_time,
            "game_name": game.game_name,
        }
        for a in game.achievements
    ]
    if not rows:
        return
 
    async with SessionLocal() as session:
        stmt = pg_insert(Achievement).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["steam_id", "appid", "api_name"],
            set_={
                "achieved": stmt.excluded.achieved,
                "unlock_time": stmt.excluded.unlock_time,
            },
        )
        await session.execute(stmt)
        await session.commit()
 
 
async def get_active_webhooks(steam_id: str) -> list[Webhook]:
    """Henter alle aktive webhook-URLer for en gitt Steam-bruker."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(
                Webhook.steam_id == steam_id,
                Webhook.is_active == True,
            )
        )
        return result.scalars().all()
 
 
# ---------------------------------------------------------------------------
# Diff-logikk
# ---------------------------------------------------------------------------
 
def find_new_unlocks(
    existing: set[str],
    game: GameAchievements,
) -> list:
    """
    Sammenligner achievements vi har i DB mot det Steam returnerer.
    Returnerer kun achievements som er NYlig låst opp.
 
    """
    return [
        a for a in game.achievements
        if a.achieved == 1 and a.api_name not in existing
    ]
 
 
# ---------------------------------------------------------------------------
# Webhook-utsending
# ---------------------------------------------------------------------------
 
async def dispatch_webhooks(
    webhooks: list[Webhook],
    steam_id: str,
    game: GameAchievements,
    new_achievements: list,
) -> None:
    if not webhooks or not new_achievements:
        return


    # Slack-payload
    achievement_lines = "\n".join(
        f"• *{a.name or a.api_name}* – {a.description}" 
        for a in new_achievements
    )
    slack_payload = {
        "text": f"🏆 *{game.game_name}* – {len(new_achievements)} nye achievements!\n{achievement_lines}"
    }

    send_webhook(slack_payload)  # Send til Slack først (hvis satt opp)

# ---------------------------------------------------------------------------
# Hoved-poll-funksjon
# ---------------------------------------------------------------------------
 
async def poll_user(steam_id: str) -> None:
    """
    Kjører én full poll-syklus for en Steam-bruker:
      1. Henter spill + achievements fra Steam
      2. Oppdaterer databasen
      3. Sender webhooks for nye unlocks
    """
    print(f"\n🔄 Starter polling for Steam ID: {steam_id}")
    print(f"   Tidspunkt: {datetime.now().isoformat()}")
 
    async with SteamClient(api_key=STEAM_API_KEY) as client:
        # Steg 1 – hent spill
        games = await client.get_owned_games(steam_id)
        print(f"   Spill funnet: {len(games)}")
 
        # Steg 2 – lagre spill i DB
        await upsert_games(steam_id, games)
 
        # Steg 3 – hent achievements for alle spill parallelt
        all_game_achievements = await client.get_all_achievements(steam_id, games)
        print(f"   Spill med achievements: {len(all_game_achievements)}")
 
    # Steg 4 – hent aktive webhooks én gang (gjelder alle spill)
    webhooks = await get_active_webhooks(steam_id)
 
    # Steg 5 – diff og lagre per spill
    total_new = 0
    for game in all_game_achievements:
        existing = await get_existing_achievements(steam_id, game.appid)
        new_unlocks = find_new_unlocks(existing, game)
 
        await upsert_achievements(steam_id, game)

        if new_unlocks:
            total_new += len(new_unlocks)
            print(f"   🏆 {game.game_name}: {len(new_unlocks)} nytt!")

            for a in new_unlocks:
                print(f"{a.api_name}")
 
    if total_new == 0:
        print("   Ingen nye achievements siden sist.")
    else:
        print(f"\n✅ Poll ferdig – {total_new} nye achievements totalt")
        webhook_message = f"🎉 {total_new} new achievements unlocked!"
        send_webhook({"text": webhook_message})

 
 
# ---------------------------------------------------------------------------
# Kjør manuelt for å teste (python poller.py)
# ---------------------------------------------------------------------------
 
