import os
import requests
from dotenv import load_dotenv

load_dotenv()  # loads .env file

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def notify_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] Missing Telegram credentials.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        print(f"[INFO] Notified Telegram: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[ERROR] Telegram notify failed: {e}")
