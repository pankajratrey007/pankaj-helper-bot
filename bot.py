import os
import asyncio
import time
import re
import yt_dlp
from dotenv import load_dotenv
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, DocumentTooBig

# =========================
# CONFIG - FIXED & CLEAN
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("❌ Missing BOT_TOKEN, API_ID or API_HASH in .env or Railway Variables!")

DOWNLOAD_DIR = "downloads"
MAX_PARALLEL_DOWNLOADS = 4          # Change if your server is strong
AUTO_DELETE_TIME = 1800             # 30 minutes
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB Telegram limit

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client("adult_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
    text = f"⬇ Downloading...\n`[{bar}] {percent:.1f}%`\n`{mb_current}MB / {mb_total}MB`"
    try:
        await message.edit(text)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except:
        pass  # ignore other edit errors

# =========================
# AUTO DELETE
# =========================
async def auto_delete(file_path):
    await asyncio.sleep(AUTO_DELETE_TIME)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass

# =========================
# DOWNLOAD FUNCTION (Improved for adult sites)
# =========================
async def download_video(url, msg):
    loop = asyncio.get_event_loop()

    def run():
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                current = d.get('downloaded_bytes', 0)
                asyncio.run_coroutine_threadsafe(progress(current, total, msg), loop)

        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(uploader|unknown)s_%(title|unknown)s_%(id)s.%(ext)s',
            'quiet': True,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
            'progress_hooks': [hook],
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Good for most adult sites
            'extractor_retries': 5,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            # For xHamster/PornHub issues in 2026
            'extractor_args': {'xhamster': {'skip': ['av1']}},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if not os.path.exists(filename):
                    raise Exception("Download failed - file not found")
                
                size = os.path.getsize(filename)
                if size > MAX_FILE_SIZE:
                    os.remove(filename)
                    raise Exception("File too large (>2GB for Telegram)")
                
                return filename, info.get('title', 'Video')
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
            file, title = await download_video(url, msg)
            
            await msg.edit("📤 Uploading to Telegram...")
            await app.send_document(
                message.chat.id,
                file,
                caption=f"✅ Downloaded: {title}\n\nBot by @yourusername",
                progress=progress  # optional upload progress
            )
            
            asyncio.create_task(auto_delete(file))
            await msg.delete()
            
        except DocumentTooBig:
            await message.reply("❌ File too large for Telegram (>2GB).")
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "forbidden" in error_msg.lower():
                await message.reply("❌ Site blocked the download. Try cookies or VPN on server.")
            else:
                await message.reply(f"❌ Failed: {error_msg[:400]}\n\nTip: Update yt-dlp → `pip install -U yt-dlp`")
        finally:
            queue.task_done()

# =========================
# COMMANDS
# =========================
@app.on_message(filters.command("start"))
async def start(client, message):
    sites = "YouTube, Instagram, TikTok, Facebook, X, PornHub, xHamster, etc."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Help", callback_data="help"),
         InlineKeyboardButton("Stats", callback_data="stats")]
    ])
    await message.reply(
        f"🔥 **Adult Video Downloader Bot**\n\n"
        f"Send any video link from:\n{sites}\n\n"
        f"Queue: {queue_count} tasks",
        reply_markup=kb
    )

@app.on_message(filters.command("stats"))
async def stats(client, message):
    global queue_count
    await message.reply(f"📊 Current Queue: **{queue_count}** tasks")

# =========================
# CALLBACKS
# =========================
@app.on_callback_query()
async def callbacks(client, query):
    await query.answer()
    if query.data == "help":
        text = (
            "✅ **Supported Sites:** YouTube, Instagram, TikTok, Facebook, X (Twitter), "
            "PornHub, xHamster, XVideos, and 1000+ more.\n\n"
            "❌ Private videos may need cookies.\n"
            "Tip: Keep yt-dlp updated for best adult site support."
        )
        await query.message.edit(text)
    elif query.data == "stats":
        global queue_count
        await query.message.edit(f"📊 Current Queue: **{queue_count}** tasks")

# =========================
# LINK HANDLER
# =========================
url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

@app.on_message(filters.text & filters.regex(url_pattern))
async def link_handler(client, message):
    global queue_count
    url = message.text.strip()
    queue_count += 1
    await queue.put((url, message))
    await message.reply(f"⏳ Added to queue! Total tasks: **{queue_count}**")

# =========================
# MAIN
# =========================
async def main():
    global queue_count
    for _ in range(MAX_PARALLEL_DOWNLOADS):
        asyncio.create_task(worker())
    
    print("BOT FILE STARTED")
    print("BOT RUNNING - Ready to download videos!")
    
    await app.start()
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
