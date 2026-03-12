# ======================================
# 🔥 Ultimate Telegram Downloader Bot
# Stable Version (API + Queue + Auto Restart)
# ======================================

import os
import time
import math
import yt_dlp
import telebot
import sqlite3
import threading
import subprocess
from queue import Queue
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client

# ======================================
# BOT CONFIG
# ======================================

TOKEN = "8769882137:AAEanCgyfRU11WKxvO94LBn0KXvOqAPy5B4"
ADMIN_ID = 8274612882

API_ID = 39058593
API_HASH = "d78f8a54cf1bff913d24d0b1599723b1"

MAX_THREADS_PER_USER = 2
MAX_WORKERS = 1
TEMP_DIR = "downloads"
FILE_EXPIRY = 3600
CHUNK_SIZE = 1500 * 1024 * 1024

os.makedirs(TEMP_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

# ======================================
# START PYROGRAM CLIENT
# ======================================

app = Client(
    "uploader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TOKEN
)

app.start()

# ======================================
# UPDATE YT-DLP
# ======================================

def update_ytdlp():
    try:
        subprocess.run(["pip","install","-U","yt-dlp"], check=True)
    except:
        pass

update_ytdlp()

# ======================================
# DATABASE
# ======================================

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS downloads(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
url TEXT,
title TEXT,
file TEXT,
status TEXT,
timestamp TEXT
)
""")

conn.commit()

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    conn.commit()

def log_download(user_id,url,title,file,status):
    cursor.execute(
        "INSERT INTO downloads(user_id,url,title,file,status,timestamp) VALUES(?,?,?,?,?,?)",
        (user_id,url,title,file,status,datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

# ======================================
# QUEUE
# ======================================

queue = Queue()
user_threads = {}

# ======================================
# SAFE SEND (PYROGRAM)
# ======================================

def safe_send(file_path, chat_id, caption=None):

    try:

        size = os.path.getsize(file_path)

        if size <= CHUNK_SIZE:

            app.send_document(chat_id,file_path,caption=caption)

        else:

            with open(file_path,"rb") as f:

                total_chunks = math.ceil(size/CHUNK_SIZE)

                for i in range(total_chunks):

                    chunk = f.read(CHUNK_SIZE)

                    chunk_file = f"{file_path}.part{i}"

                    with open(chunk_file,"wb") as cf:
                        cf.write(chunk)

                    app.send_document(chat_id,chunk_file,caption=caption if i==0 else None)

                    os.remove(chunk_file)

        return True

    except Exception as e:

        print("UPLOAD ERROR:",e)

        return False

# ======================================
# BOT COMMANDS
# ======================================

@bot.message_handler(commands=['start'])
def start_cmd(m):

    save_user(m.chat.id)

    bot.send_message(
        m.chat.id,
        "🔥 Ultimate Downloader Bot\n\nSend any video link"
    )

# ======================================
# LINK DETECTOR
# ======================================

@bot.message_handler(func=lambda m: m.text and "http" in m.text)

def link_cmd(m):

    if user_threads.get(m.chat.id,0) >= MAX_THREADS_PER_USER:
        return bot.reply_to(m,"⚠️ Wait for current downloads")

    url = m.text.strip()

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("360p",callback_data=f"360|{url}"),
        InlineKeyboardButton("720p",callback_data=f"720|{url}"),
        InlineKeyboardButton("1080p",callback_data=f"1080|{url}"),
        InlineKeyboardButton("MP3",callback_data=f"mp3|{url}")
    )

    bot.reply_to(m,"Select quality:",reply_markup=kb)

# ======================================
# CALLBACK
# ======================================

@bot.callback_query_handler(func=lambda c: True)

def callback_cmd(c):

    q,url = c.data.split("|",1)

    chat = c.message.chat.id

    bot.send_message(chat,"⏳ Added to download queue")

    queue.put((chat,url,q))

    user_threads[chat] = user_threads.get(chat,0)+1

# ======================================
# DOWNLOAD PROCESS
# ======================================

def process(chat,url,q):

    try:

        msg = bot.send_message(chat,"⬇️ Downloading...")

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
            "retries":10,
            "fragment_retries":10,
            "socket_timeout":30
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url,download=True)

            file = ydl.prepare_filename(info)

            title = info.get("title","file")

        caption = f"📥 {title}"

        safe_send(file,chat,caption)

        log_download(chat,url,title,file,"completed")

        os.remove(file)

        bot.edit_message_text("✅ Download finished",chat,msg.message_id)

    except Exception as e:

        print("ERROR:",e)

        bot.send_message(chat,"❌ Download failed")

    finally:

        user_threads[chat] = max(user_threads.get(chat,1)-1,0)

# ======================================
# WORKER
# ======================================

def worker():

    while True:

        chat,url,q = queue.get()

        process(chat,url,q)

        queue.task_done()

# ======================================
# START WORKERS
# ======================================

for _ in range(MAX_WORKERS):

    threading.Thread(target=worker,daemon=True).start()

print("BOT STARTED")

# ======================================
# AUTO RESTART POLLING
# ======================================

while True:

    try:

        bot.infinity_polling(timeout=60,long_polling_timeout=60)

    except Exception as e:

        print("Polling error:",e)

        time.sleep(5)
