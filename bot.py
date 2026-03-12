# ======================================
# ONLY EDIT THESE VALUES
# ======================================

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882
API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

# ======================================

import telebot
import yt_dlp
import sqlite3
import threading
import os
import subprocess
import time
import requests

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from queue import Queue

# -------------------------
# BOT INIT
# -------------------------

bot = telebot.TeleBot(TOKEN)

# -------------------------
# MULTIPLE TELEGRAM UPLOADERS
# -------------------------

uploaders = [
    Client("uploader1", api_id=API_ID, api_hash=API_HASH),
    Client("uploader2", api_id=API_ID, api_hash=API_HASH),
]

for u in uploaders:
    u.start()

# -------------------------
# DATABASE
# -------------------------

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
    conn.commit()

# -------------------------
# DOWNLOAD QUEUE
# -------------------------

queue = Queue()
MAX_WORKERS = 5

# -------------------------
# START COMMAND
# -------------------------

@bot.message_handler(commands=['start'])
def start(m):

    save_user(m.chat.id)

    bot.send_message(
        m.chat.id,
        "🔥 Ultimate Downloader Bot\n\n"
        "Send ANY video link\n\n"
        "Supported:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\nand many more"
    )

# -------------------------
# ADMIN USERS COMMAND
# -------------------------

@bot.message_handler(commands=['users'])
def users(m):

    if m.chat.id == ADMIN_ID:

        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]

        bot.send_message(m.chat.id, f"👤 Total users: {count}")

# -------------------------
# LINK DETECTION
# -------------------------

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def link(m):

    url = m.text.strip()

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("360p", callback_data=f"360|{url}"),
        InlineKeyboardButton("720p", callback_data=f"720|{url}")
    )

    kb.add(
        InlineKeyboardButton("1080p", callback_data=f"1080|{url}"),
        InlineKeyboardButton("MP3", callback_data=f"mp3|{url}")
    )

    bot.reply_to(m, "Select quality:", reply_markup=kb)

# -------------------------
# BUTTON HANDLER
# -------------------------

@bot.callback_query_handler(func=lambda c: True)
def cb(c):

    quality, url = c.data.split("|")

    queue.put((c.message.chat.id, url, quality))

    position = queue.qsize()

    bot.send_message(
        c.message.chat.id,
        f"📥 Added to queue\nPosition: {position}"
    )

# -------------------------
# WORKER THREADS
# -------------------------

def worker():

    while True:

        chat, url, q = queue.get()

        try:
            process(chat, url, q)

        except Exception as e:
            bot.send_message(chat, f"❌ Error: {e}")

        queue.task_done()

for i in range(MAX_WORKERS):

    threading.Thread(
        target=worker,
        daemon=True
    ).start()

# -------------------------
# DOWNLOAD FUNCTION
# -------------------------

def process(chat, url, q):

    msg = bot.send_message(chat, "⏳ Download starting...")

    def progress(d):

        if d["status"] == "downloading":

            p = d.get("_percent_str", "")
            s = d.get("_speed_str", "")
            e = d.get("_eta_str", "")

            try:
                bot.edit_message_text(
                    f"⬇️ {p}\nSpeed {s}\nETA {e}",
                    chat,
                    msg.message_id
                )
            except:
                pass

    format_map = {
        "360": "18",
        "720": "22",
        "1080": "bestvideo+bestaudio",
        "mp3": "bestaudio"
    }

    ydl_opts = {
        "format": format_map.get(q, "best"),
        "outtmpl": "%(title)s.%(ext)s",

        "retries": 10,
        "fragment_retries": 10,

        "concurrent_fragment_downloads": 5,

        "socket_timeout": 30,

        "geo_bypass": True,
        "nocheckcertificate": True,

        "quiet": True,

        "progress_hooks": [progress],

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(url, download=True)

        file = ydl.prepare_filename(info)

        title = info.get("title", "Downloaded File")

        thumb = info.get("thumbnail")

    # -------------------------
    # DOWNLOAD THUMBNAIL
    # -------------------------

    thumb_file = None

    if thumb:

        thumb_file = "thumb.jpg"

        r = requests.get(thumb)

        with open(thumb_file, "wb") as f:
            f.write(r.content)

    size = os.path.getsize(file)

    caption = f"📥 {title}"

    uploader = uploaders[0]

    # -------------------------
    # SPLIT LARGE FILES
    # -------------------------

    if size > 1900000000:

        subprocess.call([
            "ffmpeg",
            "-i", file,
            "-c", "copy",
            "-map", "0",
            "-f", "segment",
            "-segment_time", "600",
            "part_%03d.mp4"
        ])

        for f in os.listdir():

            if f.startswith("part_"):

                uploader.send_document(
                    chat,
                    f,
                    caption=caption,
                    thumb=thumb_file
                )

                os.remove(f)

    else:

        uploader.send_document(
            chat,
            file,
            caption=caption,
            thumb=thumb_file
        )

    os.remove(file)

    if thumb_file and os.path.exists(thumb_file):
        os.remove(thumb_file)

    bot.edit_message_text(
        "✅ Download finished",
        chat,
        msg.message_id
    )

# -------------------------
# RUN BOT
# -------------------------

while True:

    try:
        bot.infinity_polling()

    except Exception as e:

        print("Bot crashed:", e)

        time.sleep(10)
