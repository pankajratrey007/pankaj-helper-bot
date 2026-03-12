import telebot
import yt_dlp
import sqlite3
import threading
import os
import subprocess
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client

# ---------------------------
# CONFIGURATION
# ---------------------------
TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882
API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

bot = telebot.TeleBot(TOKEN)
userbot = Client("uploader", api_id=API_ID, api_hash=API_HASH)

# ---------------------------
# DATABASE
# ---------------------------
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
    conn.commit()

# ---------------------------
# QUEUE SYSTEM
# ---------------------------
queue = []
MAX_WORKERS = 5  # parallel downloads

# ---------------------------
# /start COMMAND
# ---------------------------
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send a video link from:\n"
        "YouTube / Instagram / TikTok / Facebook\n\n"
        "Choose the quality, the bot downloads automatically."
    )

# ---------------------------
# LINK DETECT & QUALITY SELECT
# ---------------------------
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def quality_select(message):
    url = message.text
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("360p", callback_data=f"360|{url}"),
        InlineKeyboardButton("720p", callback_data=f"720|{url}")
    )
    markup.add(
        InlineKeyboardButton("1080p", callback_data=f"1080|{url}"),
        InlineKeyboardButton("MP3", callback_data=f"mp3|{url}")
    )
    bot.reply_to(message, "🎬 Select quality:", reply_markup=markup)

# ---------------------------
# BUTTON CLICK HANDLER
# ---------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    try:
        quality, url = call.data.split("|")
        queue.append((call.message.chat.id, url, quality))
        bot.send_message(call.message.chat.id, "📥 Added to download queue")
    except:
        bot.send_message(call.message.chat.id, "❌ Failed to add to queue")

# ---------------------------
# WORKER SYSTEM (Multi-server / Parallel)
# ---------------------------
def worker():
    while True:
        if queue:
            chat_id, url, quality = queue.pop(0)
            process(chat_id, url, quality)
        else:
            time.sleep(1)

for _ in range(MAX_WORKERS):
    threading.Thread(target=worker, daemon=True).start()

# ---------------------------
# DOWNLOAD FUNCTION
# ---------------------------
def process(chat_id, url, quality):
    status = bot.send_message(chat_id, "⏳ Starting download...")

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', '0')
            eta = d.get('_eta_str', '0')
            try:
                bot.edit_message_text(
                    f"⬇️ Downloading\n\nProgress: {percent}\nSpeed: {speed}\nETA: {eta}",
                    chat_id,
                    status.message_id
                )
            except:
                pass

    format_code = {
        "360": "18",
        "720": "22",
        "1080": "137+140",
        "mp3": "bestaudio"
    }

    ydl_opts = {
        "format": format_code.get(quality, "best"),
        "outtmpl": "%(title)s.%(ext)s",
        "retries": 25,
        "fragment_retries": 25,
        "concurrent_fragment_downloads": 5,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "socket_timeout": 30,
        "progress_hooks": [progress_hook]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = ydl.prepare_filename(info)
            site = info.get("extractor", "unknown")

        bot.send_message(chat_id, f"🌐 Source detected: {site}")

        size = os.path.getsize(file)

        # ---------------------------
        # SPLIT LARGE FILES > 2GB
        # ---------------------------
        if size > 1900000000:
            bot.send_message(chat_id, "📦 Splitting large video...")
            subprocess.call([
                "ffmpeg", "-i", file, "-c", "copy", "-map", "0",
                "-f", "segment", "-segment_time", "600", "part_%03d.mp4"
            ])
            for f in os.listdir():
                if f.startswith("part_"):
                    with open(f, "rb") as vid:
                        userbot.start()
                        userbot.send_document(chat_id, vid)
                        userbot.stop()
                    os.remove(f)
        else:
            with open(file, "rb") as vid:
                userbot.start()
                userbot.send_document(chat_id, vid)
                userbot.stop()

        os.remove(file)
        bot.edit_message_text("✅ Download completed!", chat_id, status.message_id)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Download failed. Try another link.\nError: {e}",
            chat_id, status.message_id
        )

# ---------------------------
# BROADCAST COMMAND
# ---------------------------
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast ", "")
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    for u in users:
        try:
            bot.send_message(u[0], text)
        except:
            pass
    bot.send_message(message.chat.id, "✅ Broadcast sent.")

# ---------------------------
# REPLY USER COMMAND
# ---------------------------
@bot.message_handler(commands=['reply'])
def reply_user(message):
    if message.chat.id != ADMIN_ID:
        return
    try:
        parts = message.text.split(" ", 2)
        uid = int(parts[1])
        text = parts[2]
        bot.send_message(uid, text)
        bot.send_message(message.chat.id, "✅ Message sent.")
    except:
        bot.send_message(message.chat.id, "Usage:\n/reply USER_ID message")

# ---------------------------
# RUN BOT SAFELY
# ---------------------------
while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {e}")
        time.sleep(5)
