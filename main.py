"""
main.py - Hovedfil for Steam Achievement Tracker
This file will have a schedule which runs the poller every 15 minutes,
"""

import asyncio
import os
import signal
import sys
 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
 
from database import check_connection, init_db
from poller import poll_user
 
load_dotenv()

STEAM_USER_ID = os.getenv("STEAM_USER_ID")
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", 15))

def handle_shutdown(scheduler: AsyncIOScheduler):
    print("Shutting down gracefully...")
    scheduler.shutdown(wait=False)
    sys.exit(0)

async def main():
    print("Starting Steam Achievement Tracker...")
    print(f"Polling every {POLL_INTERVAL_MINUTES} minutes for user ID: {STEAM_USER_ID}")

    if not STEAM_USER_ID:
        raise EnvironmentError("Sett STEAM_USER_ID i .env")
    if not os.getenv("STEAM_API_KEY"):
        raise EnvironmentError("Sett STEAM_API_KEY i .env")
    
    print("Checking database connection...")
    for attempt in range(5):
        if await check_connection():
            print("Database connection successful!")
            break
        else:
            print(f"Database connection failed (attempt {attempt + 1}/5). quitting.")
            sys.exit(1)

    await init_db()
   
    await poll_user(STEAM_USER_ID)  # Kjør en gang ved oppstart


    #Set up scheduler to run poll_user every 15 minutes
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll_user, trigger=IntervalTrigger(minutes=POLL_INTERVAL_MINUTES),
                        args=[STEAM_USER_ID])
    scheduler.start()
    #print each time the scheduler runs


    print(f"\n✅ Scheduler kjører – neste poll om 15 minutt")
    print("   Trykk CTRL+C for å stoppe\n")
    while True:
        await asyncio.sleep(1)
    
#test run 
asyncio.run(main())