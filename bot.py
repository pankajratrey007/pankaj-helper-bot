import os
import time
import math
import yt_dlp
import telebot
import sqlite3
import threading
from queue import Queue
from pyrogram import Client
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ======================================
# CONFIG
# ======================================

TOKEN =
"8769882137:AAEanCgyfRU11WKxvO94LBn0KXvOqAPy5B4"
ADMIN_ID = 8274612882

API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

TEMP_DIR = "downloads"
MAX_WORKERS = 3
CHUNK_SIZE = 1500 * 1024 * 1024

os.makedirs(TEMP_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

app = Client(
    "uploader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TOKEN
)

app.start()

# ======================================
# DATABASE
# ======================================

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    conn.commit()

# ======================================
# QUEUE
# ======================================

queue = Queue()

# ======================================
# SAFE FILE SEND
# ======================================

def safe_send(file_path, chat):

    size = os.path.getsize(file_path)

    if size <= CHUNK_SIZE:

        app.send_document(chat, file_path)

    else:

        with open(file_path,"rb") as f:

            part = 1

            while True:

                chunk = f.read(CHUNK_SIZE)

                if not chunk:
                    break

                part_file = f"{file_path}.part{part}"

                with open(part_file,"wb") as pf:
                    pf.write(chunk)

                app.send_document(chat, part_file)

                os.remove(part_file)

                part += 1

# ======================================
# START COMMAND
# ======================================

@bot.message_handler(commands=['start'])

def start(m):

    save_user(m.chat.id)

    bot.send_message(
        m.chat.id,
        "🔥 Ultimate Downloader Bot\n\nSend any video link."
    )

# ======================================
# LINK DETECTOR
# ======================================

@bot.message_handler(func=lambda m: m.text and "http" in m.text)

def link_handler(m):

    url = m.text.strip()

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("360p",callback_data=f"360|{url}"),
        InlineKeyboardButton("720p",callback_data=f"720|{url}")
    )

    kb.add(
        InlineKeyboardButton("1080p",callback_data=f"1080|{url}"),
        InlineKeyboardButton("MP3",callback_data=f"mp3|{url}")
    )

    bot.reply_to(m,"Select quality:",reply_markup=kb)

# ======================================
# CALLBACK
# ======================================

@bot.callback_query_handler(func=lambda c: True)

def callback(c):

    q,url = c.data.split("|",1)

    chat = c.message.chat.id

    bot.send_message(chat,"⏳ Added to queue")

    queue.put((chat,url,q))

# ======================================
# DOWNLOAD FUNCTION
# ======================================

def download(chat,url,q):

    try:

        msg = bot.send_message(chat,"⬇ Downloading...")

        format_map = {
            "360":"18",
            "720":"22",
            "1080":"bestvideo+bestaudio",
            "mp3":"bestaudio"
        }

        ydl_opts = {
            "format":format_map.get(q,"best"),
            "outtmpl":f"{TEMP_DIR}/%(title)s.%(ext)s",
            "quiet":True,
            "retries":10
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url,download=True)

            file = ydl.prepare_filename(info)

        safe_send(file, chat)

        os.remove(file)

        bot.edit_message_text("✅ Download finished",chat,msg.message_id)

    except Exception as e:

        bot.send_message(chat,"❌ Download failed")

# ======================================
# WORKER
# ======================================

def worker():

    while True:

        chat,url,q = queue.get()

        download(chat,url,q)

        queue.task_done()

# ======================================
# START WORKERS
# ======================================

for i in range(MAX_WORKERS):

    threading.Thread(target=worker,daemon=True).start()

print("BOT STARTED")

# ======================================
# AUTO RESTART
# ======================================

while True:

    try:

        bot.infinity_polling(timeout=60,long_polling_timeout=60)

    except Exception as e:

        print("Restarting...",e)

        time.sleep(5)
