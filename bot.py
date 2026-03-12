import telebot
import yt_dlp
import sqlite3
import threading
import os
import subprocess
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client

# CONFIG
BOT_TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882

API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

bot = telebot.TeleBot(BOT_TOKEN)

# USER UPLOADER
uploader = Client("uploader", api_id=API_ID, api_hash=API_HASH)
uploader.start()

# DATABASE
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    conn.commit()

# QUEUE
queue = []
MAX_WORKERS = 5

# START
@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send video link\n"
        "YouTube / Instagram / TikTok / Facebook"
    )

# LINK DETECT
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def quality_select(message):

    url = message.text

    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton("360p",callback_data=f"360|{url}"),
        InlineKeyboardButton("720p",callback_data=f"720|{url}")
    )

    markup.add(
        InlineKeyboardButton("1080p",callback_data=f"1080|{url}"),
        InlineKeyboardButton("MP3",callback_data=f"mp3|{url}")
    )

    bot.reply_to(message,"🎬 Select quality:",reply_markup=markup)

# BUTTON
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    quality,url = call.data.split("|")

    queue.append((call.message.chat.id,url,quality))

    bot.send_message(call.message.chat.id,"📥 Added to queue")

# WORKER
def worker():

    while True:

        if queue:

            chat_id,url,quality = queue.pop(0)

            process(chat_id,url,quality)

        else:
            time.sleep(1)

# START WORKERS
for i in range(MAX_WORKERS):
    threading.Thread(target=worker,daemon=True).start()

# DOWNLOAD PROCESS
def process(chat_id,url,quality):

    status = bot.send_message(chat_id,"⏳ Starting download...")

    def progress_hook(d):

        if d['status'] == 'downloading':

            percent = d.get('_percent_str','0%')
            speed = d.get('_speed_str','0')
            eta = d.get('_eta_str','0')

            try:

                bot.edit_message_text(
                    f"⬇️ Downloading\n\nProgress: {percent}\nSpeed: {speed}\nETA: {eta}",
                    chat_id,
                    status.message_id
                )

            except:
                pass

    try:

        format_code = {
            "360":"18",
            "720":"22",
            "1080":"137+140",
            "mp3":"bestaudio"
        }

        ydl_opts = {

            "format": format_code.get(quality,"best"),
            "outtmpl": "video.%(ext)s",

            "retries": 30,
            "fragment_retries": 30,
            "file_access_retries": 10,
            "extractor_retries": 5,

            "concurrent_fragment_downloads": 8,

            "noplaylist": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "restrictfilenames": True,

            "socket_timeout": 30,

            "http_headers": {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9"
            },

            "progress_hooks":[progress_hook]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url,download=True)

            file = ydl.prepare_filename(info)

            site = info.get("extractor","unknown")

        bot.send_message(chat_id,f"🌐 Source: {site}")

        size = os.path.getsize(file)

        if size > 1900000000:

            bot.send_message(chat_id,"📦 Splitting video...")

            subprocess.call([
                "ffmpeg","-i",file,
                "-c","copy",
                "-map","0",
                "-segment_time","600",
                "-f","segment",
                "part_%03d.mp4"
            ])

            for f in os.listdir():

                if f.startswith("part_"):

                    uploader.send_document(chat_id,f)

                    os.remove(f)

        else:

            uploader.send_document(chat_id,file)

        os.remove(file)

        bot.edit_message_text(
            "✅ Download completed!",
            chat_id,
            status.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed. Try another link.",
            chat_id,
            status.message_id
        )

# RUN BOT
while True:

    try:
        bot.infinity_polling(timeout=60,long_polling_timeout=60)

    except:
        time.sleep(5)
