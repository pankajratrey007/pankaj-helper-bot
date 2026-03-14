print("BOT FILE STARTED")

import os
import asyncio
import yt_dlp
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8769882137:AAE9KK344JsfWx4ZXxwXzrwEC4XSrp305f0"
API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

DOWNLOAD_DIR = "downloads"
MAX_PARALLEL_DOWNLOADS = 4
AUTO_DELETE_TIME = 1800  # 30 minutes

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(
    "premium_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

queue = asyncio.Queue()

# =========================
# PROGRESS BAR
# =========================
async def progress(current, total, message):
    if total == 0:
        return
    percent = current * 100 / total
    bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
    text = f"""
⬇ Downloading

[{bar}] {percent:.1f} %

{current//1024//1024}MB / {total//1024//1024}MB
"""
    try:
        await message.edit(text)
    except:
        pass

# =========================
# AUTO DELETE FILES
# =========================
async def auto_delete(file):
    await asyncio.sleep(AUTO_DELETE_TIME)
    if os.path.exists(file):
        os.remove(file)

# =========================
# DOWNLOAD FUNCTION
# =========================
async def download_video(url, msg):
    loop = asyncio.get_event_loop()
    def run():
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes', 0)
                current = d.get('downloaded_bytes', 0)
                asyncio.run_coroutine_threadsafe(
                    progress(current, total, msg), loop
                )

        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "quiet": True,
            "retries": 10,
            "fragment_retries": 10,
            "continuedl": True,
            "progress_hooks": [hook],
            "format": "bestvideo+bestaudio/best",  # Best quality for video sites
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    return await loop.run_in_executor(None, run)

# =========================
# WORKER
# =========================
async def worker():
    while True:
        url, message = await queue.get()
        try:
            msg = await message.reply("⬇ Starting download...")
            file = await download_video(url, msg)
            await msg.edit("📤 Uploading...")
            await message.reply_document(file)
            asyncio.create_task(auto_delete(file))
            await msg.edit("✅ Download completed")
        except Exception as e:
            await message.reply(f"❌ Download failed: {e}")
        queue.task_done()

# =========================
# START COMMAND
# =========================
@app.on_message(filters.command("start"))
async def start(client, message):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="help")]])
    await message.reply("🔥 Premium Downloader Bot\n\nSend any video link.", reply_markup=kb)

# =========================
# HELP BUTTON
# =========================
@app.on_callback_query()
async def help_button(client, query):
    if query.data == "help":
        await query.message.edit(
            "Supported sites:\n\nYouTube\nInstagram\nTikTok\nFacebook\nX\nPornHub\nXHamster\n\nSend any video link."
        )

# =========================
# LINK HANDLER
# =========================
@app.on_message(filters.text & filters.regex("http"))
async def link_handler(client, message):
    url = message.text.strip()
    await queue.put((url, message))
    await message.reply("⏳ Added to queue")

# =========================
# MAIN
# =========================
async def main():
    for _ in range(MAX_PARALLEL_DOWNLOADS):
        asyncio.create_task(worker())
    try:
        await app.start()
        print("BOT RUNNING")
        await idle()
    except FloodWait as e:
        print(f"FloodWait detected. Sleeping for {e.value} seconds")
        await asyncio.sleep(e.value)

if __name__ == "__main__":
    asyncio.run(main())
