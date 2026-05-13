#Create webhooks to notify users of new achievements. This file contains the database model for webhooks and functions to manage them.
import os

 
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
 
from database import SessionLocal, Webhook, init_db

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def send_webhook(payload: dict) -> None:
    """Sender en POST-forespørsel til alle registrerte webhooks med gitt payload."""
    if not WEBHOOK_URL:
        print("WEBHOOK_URL ikke satt i .env, hopper over webhook-kall.")
        return
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Webhook sendt: {payload}")
    except requests.RequestException as e:
        print(f"Feil ved sending av webhook: {e}")
