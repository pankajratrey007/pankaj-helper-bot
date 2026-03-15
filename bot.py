print("BOT FILE STARTED")

import os
import asyncio
import time
import yt_dlp
from dotenv import load_dotenv  # pip install python-dotenv
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, DocumentTooBig

# Load .env
load_dotenv()

# =========================
# CONFIG - Use .env now
# =========================
BOT_TOKEN = os.getenv("8769882137:AAE9KK344JsfWx4ZXxwXzrwEC4XSrp305f0")
API_ID = int(os.getenv("39058593"))
API_HASH = os.getenv("d78f8a54cf1bff913d24d0b1599723b1")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("Missing credentials in .env file!")

DOWNLOAD_DIR = "downloads"
MAX_PARALLEL_DOWNLOADS = 4
AUTO_DELETE_TIME = 1800  # 30 minutes
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB Telegram limit

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client("premium_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

queue = asyncio.Queue()
queue_count = 0

# =========================
# PROGRESS BAR
# =========================
async def progress(current, total, message):
    if total == 0:
        return
    percent = min(100, (current * 100 / total))
    bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
    mb_current = current // 1024 // 1024
    mb_total = total // 1024 // 1024
    text = f"⬇ Downloading

`[{bar}] {percent:.1f}%`
`{mb_current}MB / {mb_total}MB`"
    try:
        await message.edit(text)
    except FloodWait as e:
        await asyncio.sleep(e.value)

# =========================
# AUTO DELETE
# =========================
async def auto_delete(file_path):
    await asyncio.sleep(AUTO_DELETE_TIME)
    if os.path.exists(file_path):
        os.remove(file_path)

# =========================
# DOWNLOAD FUNCTION
# =========================
async def download_video(url, msg):
    loop = asyncio.get_event_loop()
    def run():
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                current = d.get('downloaded_bytes', 0)
                asyncio.run_coroutine_threadsafe(progress(current, total, msg), loop)

        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(uploader)s_%(title|unknown)s_%(id)s.%(ext)s',  # Unique filename
            'quiet': True,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
            'progress_hooks': [hook],
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'extractor_retries': 3,  # Handle extractor errors
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if os.path.getsize(filename) > MAX_FILE_SIZE:
                    os.remove(filename)
                    raise Exception("File too large (>2GB)")
                return filename
        except Exception as e:
            raise Exception(f"yt-dlp error: {str(e)}")

    return await loop.run_in_executor(None, run)

# =========================
# WORKER
# =========================
async def worker():
    global queue_count
    while True:
        url, message = await queue.get()
        queue_count -= 1
        try:
            msg = await message.reply("⬇ Starting download...")
            file = await download_video(url, msg)
            await msg.edit("📤 Uploading...")
            await app.send_document(message.chat.id, file, caption="✅ Downloaded!")
            asyncio.create_task(auto_delete(file))
            await msg.delete()
        except DocumentTooBig:
            await message.reply("❌ File too large for Telegram (>2GB).")
        except Exception as e:
            await message.reply(f"❌ Failed: {str(e)}
Try updating yt-dlp: `pip install -U yt-dlp`")
        queue.task_done()

# =========================
# COMMANDS
# =========================
@app.on_message(filters.command("start"))
async def start(client, message):
    sites = "YouTube, Instagram, TikTok, Facebook, X (Twitter), etc."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="help"), InlineKeyboardButton("Stats", callback_data="stats")]])
    await message.reply(f"🔥 Premium Downloader Bot

Send video links from {sites}.
Queue: 0", reply_markup=kb)

@app.on_message(filters.command("stats"))
async def stats(client, message):
    global queue_count
    await message.reply(f"📊 Queue: {queue_count} tasks")

# =========================
# CALLBACKS
# =========================
@app.on_callback_query()
async def callbacks(client, query):
    await query.answer()
    if query.data == "help":
        text = "✅ Supported: YouTube, Instagram, TikTok, Facebook, X, PornHub, etc.

❌ Private/logged-in only: Use cookies if needed.
Tip: Update yt-dlp regularly."
        await query.message.edit(text)
    elif query.data == "stats":
        global queue_count
        await query.message.edit(f"📊 Current queue: {queue_count}")

# =========================
# LINK HANDLER - Added URL validation
# =========================
import re
url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
@app.on_message(filters.text & filters.regex(url_pattern))
async def link_handler(client, message):
    global queue_count
    url = message.text.strip()
    queue_count += 1
    await queue.put((url, message))
    await message.reply(f"⏳ Added to queue ({queue_count} total)")

# =========================
# MAIN
# =========================
async def main():
    global queue_count
    for _ in range(MAX_PARALLEL_DOWNLOADS):
        asyncio.create_task(worker())
    print("BOT RUNNING")
    await app.start()
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
