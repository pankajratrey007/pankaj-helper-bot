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

# Start userbot only once (fix EOF error)
userbot = Client(
    "uploader_session",
    api_id=API_ID,
    api_hash=API_HASH
)

userbot.start()

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
# DOWNLOAD QUEUE
# ---------------------------
queue = []
MAX_WORKERS = 5

# ---------------------------
# /start COMMAND
# ---------------------------
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Pankaj Downloader Bot*\n\n"
        "Supported:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\nand many more\n\n"
        "Send any link and choose quality.",
        parse_mode="Markdown"
    )

# ---------------------------
# LINK DETECT
# ---------------------------
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def quality_select(message):

    url = message.text.strip()

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
# BUTTON HANDLER
# ---------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    try:
        quality, url = call.data.split("|")

        queue.append((call.message.chat.id, url, quality))

        bot.send_message(
            call.message.chat.id,
            "📥 Added to queue"
        )

    except:
        bot.send_message(call.message.chat.id, "❌ Queue error")

# ---------------------------
# WORKER SYSTEM
# ---------------------------
def worker():

    while True:

        if queue:

            chat_id, url, quality = queue.pop(0)

            process(chat_id, url, quality)

        else:
            time.sleep(1)

for i in range(MAX_WORKERS):

    threading.Thread(
        target=worker,
        daemon=True
    ).start()

# ---------------------------
# DOWNLOAD PROCESS
# ---------------------------
def process(chat_id, url, quality):

    status = bot.send_message(chat_id, "⏳ Download starting...")

    def progress_hook(d):

        if d['status'] == 'downloading':

            percent = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', '')
            eta = d.get('_eta_str', '')

            try:

                bot.edit_message_text(
                    f"⬇️ Downloading\n\n"
                    f"Progress: {percent}\n"
                    f"Speed: {speed}\n"
                    f"ETA: {eta}",
                    chat_id,
                    status.message_id
                )

            except:
                pass

    format_code = {

        "360": "18",
        "720": "22",
        "1080": "bestvideo+bestaudio",
        "mp3": "bestaudio"

    }

    ydl_opts = {

        "format": format_code.get(quality, "best"),

        "outtmpl": "%(title)s.%(ext)s",

        "retries": 50,

        "fragment_retries": 50,

        "concurrent_fragment_downloads": 10,

        "socket_timeout": 60,

        "noplaylist": True,

        "geo_bypass": True,

        "nocheckcertificate": True,

        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },

        "progress_hooks": [progress_hook]

    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            file = ydl.prepare_filename(info)

        size = os.path.getsize(file)

        # ---------------------------
        # SPLIT LARGE FILES
        # ---------------------------
        if size > 1900000000:

            bot.send_message(chat_id, "📦 Splitting large file...")

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

                    userbot.send_document(chat_id, f)

                    os.remove(f)

        else:

            userbot.send_document(chat_id, file)

        os.remove(file)

        bot.edit_message_text(
            "✅ Download finished!",
            chat_id,
            status.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            f"❌ Download failed\n{e}",
            chat_id,
            status.message_id
        )

# ---------------------------
# BROADCAST
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

# ---------------------------
# SAFE RUN
# ---------------------------
while True:

    try:

        bot.infinity_polling()

    except Exception as e:

        print("Bot crashed:", e)

        time.sleep(5)
