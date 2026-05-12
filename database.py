"""Access to the postgres database

Tables:
- games: user_id, name, app_id
- achievements: user_id, app_id, achievement_name, achieved (boolean)
- webhooks"""

import os
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables")
print(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
 
class Base(DeclarativeBase):
    pass
 
 
# ---------------------------------------------------------------------------
# Tabeller
# ---------------------------------------------------------------------------
 
class Game(Base):
    """
    Ett spill for én Steam-bruker.
    Upsert på (steam_id, appid) – oppdaterer navn og spilletid ved polling.
    """
    __tablename__ = "games"
 
    id               = Column(Integer, primary_key=True, autoincrement=True)
    steam_id         = Column(String, nullable=False)
    appid            = Column(Integer, nullable=False)
    name             = Column(String, nullable=False)
    playtime_forever = Column(Integer, default=0)        # Minutter totalt
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
 
    __table_args__ = (
        UniqueConstraint("steam_id", "appid", name="uq_games_steam_appid"),
    )
 
    def __repr__(self) -> str:
        return f"<Game appid={self.appid} name={self.name!r}>"
 
 
class Achievement(Base):
    """
    Én achievement for ett spill for én Steam-bruker.
    Upsert på (steam_id, appid, api_name).
 
    unlock_time er et Unix-timestamp (sekunder siden 1970).
    0 betyr ikke låst opp.
    """
    __tablename__ = "achievements"
 
    id          = Column(Integer, primary_key=True, autoincrement=True)
    steam_id    = Column(String, nullable=False)
    appid       = Column(Integer, nullable=False)
    api_name    = Column(String, nullable=False)   # Steam sin interne ID
    game_name   = Column(String, default="")       # Visningsnavn
    achieved    = Column(Boolean, default=False)
    unlock_time = Column(BigInteger, default=0)    # Unix timestamp
    created_at  = Column(DateTime, default=datetime.now)
    updated_at  = Column(DateTime, default=datetime.now, onupdate=datetime.now)
 
    __table_args__ = (
        UniqueConstraint(
            "steam_id", "appid", "api_name",
            name="uq_achievements_steam_appid_apiname",
        ),
    )
 
    def __repr__(self) -> str:
        status = "✅" if self.achieved else "🔒"
        return f"<Achievement {status} {self.api_name!r} appid={self.appid}>"
 
 
 
 
# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------
 
async def init_db() -> None:
    """
    Oppretter alle tabeller hvis de ikke finnes fra før.
    Kall denne én gang når applikasjonen starter.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database klar – tabeller opprettet/verifisert")
 
 
async def check_connection() -> bool:
    """
    Tester at vi faktisk får kontakt med Postgres.
    Returnerer True hvis OK, False hvis ikke.
    """
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"❌ Kunne ikke koble til databasen: {exc}")
        return False

