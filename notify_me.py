import os
import requests
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MESSAGE = "✅ Your Python script has completed successfully!"

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, data=payload)
    print(f"[INFO] Message status: {response.status_code}")
    print(f"[INFO] Response: {response.json()}")

# Call the function at end of any script
if __name__ == "__main__":
    send_telegram_message(BOT_TOKEN, CHAT_ID, MESSAGE)
