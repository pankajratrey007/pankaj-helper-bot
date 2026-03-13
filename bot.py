import os
import asyncio
import yt_dlp
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =============================
# CONFIG
# =============================

BOT_TOKEN = "8769882137:AAEanCgyfRU11WKxvO94LBn0KXvOqAPy5B4"
API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

DOWNLOAD_DIR = "downloads"
MAX_PARALLEL_DOWNLOADS = 4
AUTO_DELETE_TIME = 1800   # 30 minutes

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(
    "premium_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

download_queue = asyncio.Queue()

# =============================
# PROGRESS BAR
# =============================

async def progress(current, total, message):

    percent = current * 100 / total

    bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))

    text = f"""
⬇ Downloading

[{bar}] {percent:.1f}%

{current//1024//1024}MB / {total//1024//1024}MB
"""

    try:
        await message.edit(text)
    except:
        pass

# =============================
# CLEANUP
# =============================

async def auto_delete(file):

    await asyncio.sleep(AUTO_DELETE_TIME)

    if os.path.exists(file):
        os.remove(file)

# =============================
# DOWNLOAD FUNCTION
# =============================

async def download_worker():

    while True:

        url, message = await download_queue.get()

        try:

            msg = await message.reply("⬇ Starting download...")

            ydl_opts = {
                "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                "retries": 10,
                "fragment_retries": 10,
                "continuedl": True,
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=True)

                file = ydl.prepare_filename(info)

            await msg.edit("📤 Uploading...")

            sent = await message.reply_document(file)

            asyncio.create_task(auto_delete(file))

            await msg.edit("✅ Download completed")

        except Exception as e:

            await message.reply("❌ Download failed")

        download_queue.task_done()

# =============================
# START COMMAND
# =============================

@app.on_message(filters.command("start"))

async def start(client, message):

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Help", callback_data="help")]
    ])

    await message.reply(
        "🔥 Premium Downloader Bot\n\nSend any video link.",
        reply_markup=kb
    )

# =============================
# HELP BUTTON
# =============================

@app.on_callback_query()

async def callbacks(client, query):

    if query.data == "help":

        await query.message.edit(
            "Send links from:\n\n"
            "YouTube\nInstagram\nTikTok\nFacebook\nTwitter"
        )

# =============================
# LINK HANDLER
# =============================

@app.on_message(filters.text & filters.regex("http"))

async def link_handler(client, message):

    url = message.text.strip()

    await download_queue.put((url, message))

    await message.reply("⏳ Added to queue")

# =============================
# START WORKERS
# =============================

async def main():

    for _ in range(MAX_PARALLEL_DOWNLOADS):

        asyncio.create_task(download_worker())

    await app.start()

    print("BOT RUNNING")

    await idle()

from pyrogram import idle

asyncio.run(main())
