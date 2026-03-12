# ======================================
# BOT CONFIG
# ======================================

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882

API_LIST = [
    {"api_id": 39058593, "api_hash": "d78f8a54cf1bff913d24d0b1599723b1"},
    {"api_id": 39058594, "api_hash": "9a8b7c6d5e4f3g2h1i0j9k8l7m6n5o4p"},
]

MAX_THREADS_PER_USER = 2
FILE_EXPIRY = 3600

# ======================================

import telebot, yt_dlp, sqlite3, threading, os, subprocess, time, requests, random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client
from queue import Queue
from datetime import datetime

# -------------------------
# BOT INIT
# -------------------------
bot = telebot.TeleBot(TOKEN)

# -------------------------
# UPLOADERS
# -------------------------
uploaders = []
for idx, api in enumerate(API_LIST):
    uploaders.append(Client(f"uploader{idx+1}", bot_token=TOKEN, api_id=api["api_id"], api_hash=api["api_hash"]))
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
# QUEUE & THREADS
# -------------------------
queue = Queue()
MAX_WORKERS = 5
user_threads = {}
failed_uploads = []
live_progress = {}  # <user_id>: {"title":..., "percent":..., "speed":..., "eta":...}

# -------------------------
# START COMMAND
# -------------------------
@bot.message_handler(commands=['start'])
def start(m):
    save_user(m.chat.id)
    bot.send_message(
        m.chat.id,
        "🔥 Ultimate Self-Managing Downloader Bot\n\n"
        "Send any video link\nSupported: YouTube, Instagram, TikTok, Facebook, Twitter, 1000+ sites"
    )

# -------------------------
# ADMIN USERS
# -------------------------
@bot.message_handler(commands=['users'])
def users(m):
    if m.chat.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        bot.send_message(m.chat.id, f"👤 Total users: {count}")

# -------------------------
# MESSAGE LOGGING & AUTO-REPLY
# -------------------------
@bot.message_handler(func=lambda m: True)
def log_all_messages(m):
    save_user(m.chat.id)
    print(f"[{datetime.now()}] {m.chat.id}: {m.text}")
    if m.chat.id != ADMIN_ID:
        bot.send_message(m.chat.id, "🤖 Message received, processing your request...")

# -------------------------
# LINK DETECTION
# -------------------------
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def link(m):
    threads = user_threads.get(m.chat.id, 0)
    if threads >= MAX_THREADS_PER_USER:
        bot.reply_to(m, "⚠️ You already have max downloads running. Please wait.")
        return
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
    user_threads[c.message.chat.id] = user_threads.get(c.message.chat.id, 0) + 1
    pos = queue.qsize()
    bot.send_message(c.message.chat.id, f"📥 Added to queue\nPosition: {pos}")

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
        user_threads[chat] = max(user_threads.get(chat, 1) - 1, 0)
        if chat in live_progress:
            live_progress.pop(chat)
        queue.task_done()

for i in range(MAX_WORKERS):
    threading.Thread(target=worker, daemon=True).start()

# -------------------------
# DOWNLOAD FUNCTION WITH LIVE PROGRESS
# -------------------------
def safe_send(uploader, chat, file, caption, thumb=None):
    try:
        uploader.send_document(chat, file, caption=caption, thumb=thumb)
        return True
    except:
        failed_uploads.append({"chat": chat, "file": file})
        return False

def process(chat, url, q):
    msg = bot.send_message(chat, "⏳ Download starting...")
    format_map = {"360": "18", "720": "22", "1080": "bestvideo+bestaudio", "mp3": "bestaudio"}

    def progress(d):
        if d["status"] == "downloading":
            live_progress[chat] = {
                "title": d.get("filename", "Downloading"),
                "percent": d.get("_percent_str", ""),
                "speed": d.get("_speed_str", ""),
                "eta": d.get("_eta_str", "")
            }
            try:
                bot.edit_message_text(f"⬇️ {live_progress[chat]['percent']}\nSpeed: {live_progress[chat]['speed']}\nETA: {live_progress[chat]['eta']}", chat, msg.message_id)
            except: pass

    ydl_opts = {
        "format": format_map.get(q, "best"),
        "outtmpl": "%(title)s.%(ext)s",
        "retries": 10,
        "fragment_retries": 10,
        "quiet": True,
        "progress_hooks": [progress],
        "http_headers": {"User-Agent": "Mozilla/5.0"},
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file = ydl.prepare_filename(info)
        title = info.get("title", "Downloaded File")
        thumb = info.get("thumbnail")
        duration = info.get("duration", 0)

    thumb_file = None
    if thumb:
        thumb_file = "thumb.jpg"
        r = requests.get(thumb)
        with open(thumb_file, "wb") as f:
            f.write(r.content)

    size = os.path.getsize(file)
    caption = f"📥 {title}\n📏 Size: {round(size/1024/1024,2)} MB\n⏱ Duration: {duration} sec"
    uploader = uploaders[-1] if size > 1500000000 else random.choice(uploaders)

    # Split large files (>2GB)
    if size > 1900000000:
        subprocess.call([
            "ffmpeg", "-i", file, "-c", "copy", "-map", "0",
            "-f", "segment", "-segment_time", "600", "part_%03d.mp4"
        ])
        for f in os.listdir():
            if f.startswith("part_"):
                if not safe_send(uploader, chat, f, caption, thumb_file):
                    for u in uploaders:
                        if safe_send(u, chat, f, caption, thumb_file):
                            break
                os.remove(f)
    else:
        if not safe_send(uploader, chat, file, caption, thumb_file):
            for u in uploaders:
                if safe_send(u, chat, file, caption, thumb_file):
                    break

    os.remove(file)
    if thumb_file and os.path.exists(thumb_file):
        os.remove(thumb_file)

    bot.edit_message_text("✅ Download finished", chat, msg.message_id)
    if chat in live_progress:
        live_progress.pop(chat)

# -------------------------
# AUTO-CLEANUP THREAD
# -------------------------
def cleanup_thread():
    while True:
        now = time.time()
        for f in os.listdir():
            if f.endswith((".mp4", ".mp3")):
                if now - os.path.getctime(f) > FILE_EXPIRY:
                    os.remove(f)
        time.sleep(300)

threading.Thread(target=cleanup_thread, daemon=True).start()

# -------------------------
# ADMIN DASHBOARD WITH LIVE PROGRESS
# -------------------------
@bot.message_handler(commands=['dashboard'])
def dashboard(m):
    if m.chat.id != ADMIN_ID:
        bot.reply_to(m, "❌ You are not authorized")
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    qsize = queue.qsize()
    active_threads = sum(user_threads.values())
    failed_count = len(failed_uploads)

    msg_text = (
        f"📊 Admin Dashboard\n\n"
        f"👤 Total Users: {total_users}\n"
        f"📥 Queue Size: {qsize}\n"
        f"⚡ Active Threads: {active_threads}\n"
        f"❌ Failed Uploads: {failed_count}\n\n"
        f"💻 Live Downloads:\n"
    )

    if live_progress:
        for uid, info in live_progress.items():
            msg_text += f"• {uid}: {info['title']} {info['percent']} | Speed: {info['speed']} | ETA: {info['eta']}\n"
    else:
        msg_text += "No active downloads."

    msg_text += "\nUse /reply <user_id> <message> to message any user."
    bot.send_message(m.chat.id, msg_text)

# -------------------------
# ADMIN REPLY
# -------------------------
@bot.message_handler(commands=['reply'])
def admin_reply(m):
    if m.chat.id != ADMIN_ID:
        return
    try:
        parts = m.text.split(" ", 2)
        target_id = int(parts[1])
        reply_text = parts[2]
        bot.send_message(target_id, f"💬 Admin: {reply_text}")
        bot.reply_to(m, f"✅ Message sent to {target_id}")
    except:
        bot.reply_to(m, "⚠️ Usage: /reply <user_id> <message>")

# -------------------------
# RUN BOT
# -------------------------
print("BOT STARTED")
while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        print("Bot crashed:", e)
        time.sleep(5)
