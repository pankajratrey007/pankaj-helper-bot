# ======================================
# ONLY EDIT THESE 4 VALUES
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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from queue import Queue

bot = telebot.TeleBot(TOKEN)

# uploader account
uploader = Client(
    "uploader",
    api_id=API_ID,
    api_hash=API_HASH
)

uploader.start()

# -------------------------
# DATABASE
# -------------------------

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)"
)

conn.commit()

def save_user(uid):
    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES(?)",
        (uid,)
    )
    conn.commit()

# -------------------------
# DOWNLOAD QUEUE
# -------------------------

queue = Queue()

MAX_WORKERS = 5

# -------------------------
# START
# -------------------------

@bot.message_handler(commands=['start'])
def start(m):

    save_user(m.chat.id)

    bot.send_message(
        m.chat.id,
        "🔥 Ultimate Downloader Bot\n\n"
        "Send ANY video link\n\n"
        "Supported sites:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\nand 1000+ more"
    )

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

    bot.reply_to(
        m,
        "Select quality:",
        reply_markup=kb
    )

# -------------------------
# BUTTON HANDLER
# -------------------------

@bot.callback_query_handler(func=lambda c: True)
def cb(c):

    quality, url = c.data.split("|")

    queue.put((c.message.chat.id, url, quality))

    bot.send_message(
        c.message.chat.id,
        "📥 Added to queue"
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

        "retries": 50,
        "fragment_retries": 50,

        "concurrent_fragment_downloads": 10,

        "socket_timeout": 60,

        "nocheckcertificate": True,
        "geo_bypass": True,

        "progress_hooks": [progress],

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        }

    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(url, download=True)

        file = ydl.prepare_filename(info)

        title = info.get("title", "Downloaded File")

    size = os.path.getsize(file)

    caption = f"📥 {title}"

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
                    caption=caption
                )

                os.remove(f)

    else:

        uploader.send_document(
            chat,
            file,
            caption=caption
        )

    os.remove(file)

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

        print(e)

        time.sleep(5)
