import os
import sys
from pathlib import Path
import asyncio

# Add this block:
if sys.platform.startswith('win'):
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        print("Please install nest_asyncio: pip install nest_asyncio")

from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes

TEST_IMAGE_PATH = Path(r"D:\Comfy_UI_V20\ComfyUI\output\dancer\test.jpeg")
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file.")
    sys.exit(1)

try:
    CHAT_ID = int(CHAT_ID)
except ValueError:
    print("ERROR: TELEGRAM_CHAT_ID in .env must be a valid integer.")
    sys.exit(1)

async def send_image_with_buttons(bot: Bot) -> int:
    if not TEST_IMAGE_PATH.exists():
        print(f"ERROR: Test image not found at {TEST_IMAGE_PATH}")
        sys.exit(1)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve|{TEST_IMAGE_PATH}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"reject|{TEST_IMAGE_PATH}")
        ]
    ])

    with open(TEST_IMAGE_PATH, "rb") as photo_file:
        msg = await bot.send_photo(
            chat_id=CHAT_ID,
            photo=photo_file,
            caption=f"🔍 Please review and choose an action:",
            reply_markup=keyboard
        )

    print(f"[INFO] Sent image with message_id = {msg.message_id}")
    return msg.message_id

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    action, encoded_path = query.data.split("|", 1)
    img_path = Path(encoded_path).resolve()
    msg_id_to_delete = query.message.message_id

    try:
        await context.bot.delete_message(chat_id=CHAT_ID, message_id=msg_id_to_delete)
        print(f"[INFO] Deleted image message (message_id={msg_id_to_delete})")
    except Exception as e:
        print(f"[WARN] Could not delete message {msg_id_to_delete}: {e}")

    if action == "approve":
        print(f"[RESULT] User chose APPROVE for {img_path.name}")
    else:
        print(f"[RESULT] User chose REJECT for {img_path.name}")

    await query.answer(f"You pressed {action.upper()}")
    await asyncio.sleep(1)
    await context.application.stop()

async def main():
    bot = Bot(token=BOT_TOKEN)
    await send_image_with_buttons(bot)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(button_callback))
    print("[INFO] Telegram bot is now listening for button presses…")
    print("[INFO] Tap ✅ Approve or ❌ Reject in Telegram to continue.")
    await app.run_polling()
    print("[INFO] Bot has shut down. Exiting now.")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
