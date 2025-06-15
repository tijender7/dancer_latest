#!/usr/bin/env python
"""
send_telegram_image_approvals.py

1) Sends each image (passed as CLI args) to your Telegram chat with inline "✅ Approve" / "❌ Reject" buttons.
2) Listens for button presses, updates telegram_approvals.json, deletes the image message from chat,
   and once all images have been reviewed, posts a summary and exits.

Usage:
    python send_telegram_image_approvals.py <absolute_path_to_image1> <absolute_path_to_image2> ...

Prerequisites:
  - A .env file (in this folder or a parent) with:
        TELEGRAM_BOT_TOKEN=<your_bot_token>
        TELEGRAM_CHAT_ID=<your_numeric_chat_id>
  - python-telegram-bot v20+ and python-dotenv:
        pip install python-telegram-bot python-dotenv nest_asyncio
"""

import os
import sys
import json
import hashlib
import asyncio
from pathlib import Path

# ─── Fix for Windows / Jupyter "event loop already running" ────────────────────
if sys.platform.startswith('win'):
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        print("Please install nest_asyncio: pip install nest_asyncio")

# ─── Telegram Libraries ─────────────────────────────────────────────────────────
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes

# ─── Configuration / State Files ────────────────────────────────────────────────
SCRIPT_DIR        = Path(__file__).resolve().parent
APPROVALS_JSON    = SCRIPT_DIR / "telegram_approvals.json"
TOKEN_MAP_JSON    = SCRIPT_DIR / "token_map.json"

# ─── Load environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) ──────────
load_dotenv()  # expects a .env in this folder or a parent
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
    sys.exit(1)

try:
    CHAT_ID = int(CHAT_ID)
except ValueError:
    print("ERROR: TELEGRAM_CHAT_ID must be a valid integer")
    sys.exit(1)

# ─── Collect image file paths from command-line arguments ───────────────────────
if len(sys.argv) < 2:
    print("Usage: python send_telegram_image_approvals.py <image1> <image2> ...")
    sys.exit(1)

image_files = [Path(p).resolve() for p in sys.argv[1:]]
for img in image_files:
    if not img.exists():
        print(f"ERROR: File not found on disk: {img}")
        sys.exit(1)

# ─── Load or initialize image_states from telegram_approvals.json ────────────────
# image_states: { "<abs_path>": {"status": None/"approve"/"reject", "message_id": <int>} }
if APPROVALS_JSON.exists():
    try:
        with open(APPROVALS_JSON, "r", encoding="utf-8") as f:
            image_states = json.load(f)
    except Exception:
        image_states = {}
else:
    image_states = {}

# Initialize any new image paths that aren't in the JSON yet
for img in image_files:
    img_str = str(img)
    if img_str not in image_states:
        image_states[img_str] = {"status": None, "message_id": None}

# ─── Generate or load token_to_path mapping ───────────────────────────────────────
# token_to_path: { "<short_token>": "<abs_path>" }
if TOKEN_MAP_JSON.exists():
    try:
        with open(TOKEN_MAP_JSON, "r", encoding="utf-8") as f:
            token_to_path = json.load(f)
    except Exception:
        token_to_path = {}
else:
    token_to_path = {}

# Generate short token for any new image paths
def make_short_token(abs_path: str) -> str:
    """
    Generate a deterministic 10-byte hex token for the given absolute path.
    (We keep it short so the callback_data stays under Telegram limits.)
    """
    h = hashlib.md5(abs_path.encode("utf-8")).hexdigest()
    return h[:10]

for img in image_files:
    img_str = str(img)
    # If this absolute path is not yet tokenized, create a token
    if img_str not in token_to_path.values():
        existing = [t for t, p in token_to_path.items() if p == img_str]
        if not existing:
            token = make_short_token(img_str)
            # If collision (very unlikely), append an index until unique
            suffix = 1
            base = token
            while token in token_to_path:
                token = f"{base}{suffix}"
                suffix += 1
            token_to_path[token] = img_str

# Save token_to_path to JSON immediately (in case script crashes later)
def save_token_map():
    try:
        with open(TOKEN_MAP_JSON, "w", encoding="utf-8") as f:
            json.dump(token_to_path, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Could not write {TOKEN_MAP_JSON}: {e}")

save_token_map()

# ─── Helper: Save image_states to JSON ──────────────────────────────────────────
def save_state() -> None:
    try:
        with open(APPROVALS_JSON, "w", encoding="utf-8") as f:
            json.dump(image_states, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Could not write {APPROVALS_JSON}: {e}")

# ─── Global flag to track if we're shutting down ───────────────────────────────
shutting_down = False

# ─── Async Callback Handler ──────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Called when a user taps "✅ Approve" or "❌ Reject" on an image.
    Steps:
      1) Parse callback_data: "approve|<token>" or "reject|<token>".
      2) Look up full image path via token_to_path.
      3) Update image_states[abs_path]["status"] and save.
      4) Delete the original image message from chat.
      5) If all images now have non-None status, send a summary and stop the bot.
    """
    global shutting_down
    
    if shutting_down:
        return
        
    query = update.callback_query
    if not query or not query.data:
        return

    # (callback_data comes in exactly as "approve|<token>" or "reject|<token>")
    try:
        action, token = query.data.split("|", 1)
    except ValueError:
        await query.answer("❌ Invalid callback data.")
        return

    if token not in token_to_path:
        await query.answer("❌ Unknown token.")
        return

    img_path = Path(token_to_path[token]).resolve()
    img_str = str(img_path)

    if img_str not in image_states:
        await query.answer("❌ Internal error: Image not found in state.")
        return

    # 1) Update status ("approve" or "reject")
    if action not in ("approve", "reject"):
        await query.answer("❌ Invalid action.")
        return

    image_states[img_str]["status"] = action
    save_state()

    # 2) Acknowledge and delete the image‐with‐buttons message
    await query.answer(f"Marked as {action.upper()}")
    try:
        await context.bot.delete_message(
            chat_id=CHAT_ID,
            message_id=query.message.message_id
        )
        print(f"[INFO] Deleted image message (message_id={query.message.message_id})")
    except Exception as e:
        print(f"[WARN] Could not delete Telegram message {query.message.message_id}: {e}")

    # 3) If all images have now been reviewed, send summary & shut down
    all_done = all(info["status"] is not None for info in image_states.values())
    if all_done and not shutting_down:
        shutting_down = True
        approved = [p for p, info in image_states.items() if info["status"] == "approve"]
        rejected = [p for p, info in image_states.items() if info["status"] == "reject"]

        summary_text = (
            f"📝 All images reviewed!\n\n"
            f"✅ Approved: {len(approved)}\n"
            f"❌ Rejected: {len(rejected)}"
        )
        try:
            await context.bot.send_message(chat_id=CHAT_ID, text=summary_text)
            print("[INFO] Sent summary to Telegram.")
        except Exception as e:
            print(f"[WARN] Could not send summary message: {e}")

        # Schedule shutdown after a brief delay
        print("[INFO] Scheduling shutdown...")
        asyncio.create_task(delayed_shutdown(context.application))

async def delayed_shutdown(application):
    """Shutdown the application after a brief delay."""
    await asyncio.sleep(2)  # Give time for summary message to be delivered
    print("[INFO] Shutting down application...")
    application.stop_running()

# ─── Async Function to Send All Pending Images ──────────────────────────────────
async def send_pending_images(app):
    """
    Sends every image that hasn't been sent to Telegram yet.
    - Uses app.bot.send_photo(...) so we get a message_id back.
    - Updates image_states[...] and saves JSON after each send.
    """
    bot = app.bot

    for img in image_files:
        img_str = str(img)
        state = image_states.get(img_str, {})
        if state.get("message_id") is None:
            if not img.exists():
                print(f"[ERROR] Image not found on disk: {img}")
                continue

            # Find the token for this path
            token = None
            for t, p in token_to_path.items():
                if p == img_str:
                    token = t
                    break
            if token is None:
                print(f"[ERROR] No token found for {img_str}")
                continue

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve|{token}"),
                    InlineKeyboardButton("❌ Reject",  callback_data=f"reject|{token}")
                ]
            ])
            try:
                with open(img, "rb") as photo_file:
                    msg = await bot.send_photo(
                        chat_id=CHAT_ID,
                        photo=photo_file,
                        caption=f"👀 Review: {img.name}",
                        reply_markup=keyboard
                    )
                image_states[img_str]["message_id"] = msg.message_id
                save_state()
                print(f"[INFO] Sent {img.name} as message_id {msg.message_id}")
                # Slight delay to avoid hitting Telegram rate limits
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"[ERROR] Failed to send {img}: {e}")

    print("[INFO] All (existing) images have been sent to Telegram.")

# ─── Main Async Entrypoint ──────────────────────────────────────────────────────
async def main():
    # Check if all images are already reviewed
    all_done = all(info["status"] is not None for info in image_states.values())
    if all_done:
        print("[INFO] All images have already been reviewed. Exiting.")
        return

    # Build the Telegram Application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(callback_handler))

    # 1) Send any pending images before starting the polling loop
    await send_pending_images(app)

    # 2) Start polling for button presses; run_polling() will block until shutdown()
    print("[INFO] Telegram approval bot running... awaiting button presses.")
    print("       Tap ✅ Approve or ❌ Reject in Telegram to continue.")
    
    try:
        await app.run_polling(stop_signals=None)  # Disable default signal handlers
    except Exception as e:
        print(f"[ERROR] Polling error: {e}")
    finally:
        print("[INFO] Telegram approval bot has exited (all images reviewed).")

# ─── Script Entrypoint ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user. Exiting.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
    finally:
        print("[INFO] Script finished.")