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
MAX_WORKERS = 3
FILE_EXPIRY = 3600  # seconds
TEMP_DIR = "/tmp"
MAX_RETRIES = 3

# ======================================
import telebot, yt_dlp, sqlite3, threading, os, subprocess, time, requests, random, json
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
    try:
        uploader = Client(f"uploader{idx+1}", bot_token=TOKEN, api_id=api["api_id"], api_hash=api["api_hash"])
        uploader.start()
        uploaders.append(uploader)
    except Exception as e:
        print(f"Uploader {idx+1} failed: {e}")

# -------------------------
# DATABASE
# -------------------------
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
    try:
        cursor.execute("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
        conn.commit()
    except Exception as e:
        print(f"DB save error: {e}")

def log_download(user_id, url, title, file, status):
    try:
        cursor.execute("INSERT INTO downloads(user_id, url, title, file, status, timestamp) VALUES(?,?,?,?,?,?)",
                       (user_id, url, title, file, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"History log error: {e}")

# -------------------------
# FAILED DOWNLOADS FILE
# -------------------------
FAILED_FILE = os.path.join(TEMP_DIR, "failed_downloads.json")
if os.path.exists(FAILED_FILE):
    with open(FAILED_FILE, "r") as f:
        failed_queue = json.load(f)
else:
    failed_queue = []

def save_failed_queue():
    with open(FAILED_FILE, "w") as f:
        json.dump(failed_queue, f)

# -------------------------
# QUEUE & THREADS
# -------------------------
queue = Queue()
user_threads = {}
live_progress = {}

# Re-add failed downloads on bot restart
for item in failed_queue:
    queue.put(tuple(item))

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
# ADMIN COMMANDS
# -------------------------
@bot.message_handler(commands=['users'])
def users(m):
    if m.chat.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        bot.send_message(m.chat.id, f"👤 Total users: {count}")

@bot.message_handler(commands=['dashboard'])
def dashboard(m):
    if m.chat.id != ADMIN_ID:
        bot.reply_to(m, "❌ Not authorized")
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    qsize = queue.qsize()
    active_threads = sum(user_threads.values())

    msg_text = f"📊 Admin Dashboard\n\n👤 Total Users: {total_users}\n📥 Queue Size: {qsize}\n⚡ Active Threads: {active_threads}\n\n💻 Live Downloads:\n"
    if live_progress:
        for uid, info in live_progress.items():
            msg_text += f"• {uid}: {info['title']} {info['percent']} | Speed: {info['speed']} | ETA: {info['eta']}\n"
    else:
        msg_text += "No active downloads."
    bot.send_message(m.chat.id, msg_text)

@bot.message_handler(commands=['reply'])
def admin_reply(m):
    if m.chat.id != ADMIN_ID:
        return
    try:
        parts = m.text.split(" ", 2)
        target_id = int(parts[1])
        reply_text = parts[2]
        bot.send_message(target_id, f"💬 Admin: {reply_text}")
        bot.reply_to(m, f"✅ Sent to {target_id}")
    except:
        bot.reply_to(m, "⚠️ Usage: /reply <user_id> <message>")

# -------------------------
# DOWNLOAD HISTORY COMMANDS
# -------------------------
@bot.message_handler(commands=['history'])
def history(m):
    if m.chat.id != ADMIN_ID:
        bot.reply_to(m, "❌ Not authorized")
        return
    cursor.execute("SELECT id, user_id, title, status, timestamp FROM downloads ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "No download history found.")
        return
    msg = "📜 Last 20 Downloads:\n\n"
    for r in rows:
        msg += f"ID:{r[0]} | User:{r[1]} | {r[2]} | Status:{r[3]} | {r[4]}\n"
    msg += "\nUse /retry <ID> to re-download."
    bot.send_message(m.chat.id, msg)

@bot.message_handler(commands=['retry'])
def retry(m):
    if m.chat.id != ADMIN_ID:
        return
    try:
        parts = m.text.split(" ", 1)
        dl_id = int(parts[1])
        cursor.execute("SELECT user_id, url, title FROM downloads WHERE id=?", (dl_id,))
        row = cursor.fetchone()
        if not row:
            bot.reply_to(m, "❌ Download ID not found")
            return
        user_id, url, title = row
        queue.put((user_id, url, "best", 0))
        bot.reply_to(m, f"♻️ Retry added for {title} (User {user_id})")
    except Exception as e:
        print(f"Retry error: {e}")
        bot.reply_to(m, "⚠️ Usage: /retry <download_id>")

# -------------------------
# MESSAGE LOGGING
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
        bot.reply_to(m, "⚠️ Max downloads running. Wait.")
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
    try:
        quality, url = c.data.split("|")
        queue.put((c.message.chat.id, url, quality, 0))  # retries = 0
        user_threads[c.message.chat.id] = user_threads.get(c.message.chat.id, 0) + 1
        bot.send_message(c.message.chat.id, f"📥 Added to queue (position: {queue.qsize()})")
    except Exception as e:
        print(f"Callback error: {e}")

# -------------------------
# WORKER THREADS
# -------------------------
def worker():
    while True:
        chat, url, q, retries = queue.get()
        try:
            process(chat, url, q, retries)
        except Exception as e:
            print(f"Worker error: {e}")
            if retries < MAX_RETRIES:
                queue.put((chat, url, q, retries+1))
                bot.send_message(chat, f"⚠️ Retry {retries+1} due to error...")
            else:
                bot.send_message(chat, f"❌ Failed after {MAX_RETRIES} retries. Will resume on bot restart.")
                failed_queue.append([chat, url, q, 0])
                save_failed_queue()
        user_threads[chat] = max(user_threads.get(chat, 1) - 1, 0)
        live_progress.pop(chat, None)
        queue.task_done()

for i in range(MAX_WORKERS):
    threading.Thread(target=worker, daemon=True).start()

# -------------------------
# DOWNLOAD FUNCTION WITH HISTORY & AUTO-RESUME
# -------------------------
def safe_send(uploader, chat, file, caption, thumb=None):
    try:
        uploader.send_document(chat, file, caption=caption, thumb=thumb)
        return True
    except:
        return False

def process(chat, url, q, retries=0):
    msg = bot.send_message(chat, "⏳ Download starting...")
    format_map = {"360": "18", "720": "22", "1080": "bestvideo+bestaudio", "mp3": "bestaudio"}
    last_edit = 0

    def progress(d):
        nonlocal last_edit
        if d["status"] == "downloading" and time.time() - last_edit > 2:
            live_progress[chat] = {
                "title": d.get("filename", "Downloading"),
                "percent": d.get("_percent_str", ""),
                "speed": d.get("_speed_str", ""),
                "eta": d.get("_eta_str", "")
            }
            try:
                bot.edit_message_text(f"⬇️ {live_progress[chat]['percent']} | Speed: {live_progress[chat]['speed']} | ETA: {live_progress[chat]['eta']}", chat, msg.message_id)
            except: pass
            last_edit = time.time()

    ydl_opts = {
        "format": format_map.get(q, "best"),
        "outtmpl": os.path.join(TEMP_DIR, "%(title)s.%(ext)s"),
        "retries": 10,
        "fragment_retries": 10,
        "quiet": True,
        "progress_hooks": [progress],
        "continuedl": True,
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
        thumb_file = os.path.join(TEMP_DIR, "thumb.jpg")
        r = requests.get(thumb)
        with open(thumb_file, "wb") as f:
            f.write(r.content)

    size = os.path.getsize(file)
    caption = f"📥 {title}\n📏 Size: {round(size/1024/1024,2)} MB\n⏱ Duration: {duration} sec"
    uploader = uploaders[-1] if size > 1500000000 else random.choice(uploaders)

    try:
        # Split large files safely
        if size > 1900000000:
            subprocess.call([
                "ffmpeg", "-i", file, "-c", "copy", "-map", "0",
                "-f", "segment", "-segment_time", "600", os.path.join(TEMP_DIR, "part_%03d.mp4")
            ])
            for f in os.listdir(TEMP_DIR):
                if f.startswith("part_"):
                    fpath = os.path.join(TEMP_DIR, f)
                    if not safe_send(uploader, chat, fpath, caption, thumb_file):
                        for u in uploaders:
                            if safe_send(u, chat, fpath, caption, thumb_file):
                                break
                    os.remove(fpath)
        else:
            if not safe_send(uploader, chat, file, caption, thumb_file):
                for u in uploaders:
                    if safe_send(u, chat, file, caption, thumb_file):
                        break
        log_download(chat, url, title, file, "Completed")
    except Exception as e:
        log_download(chat, url, title, file, "Failed")
        print(f"Error sending: {e}")

    if os.path.exists(file): os.remove(file)
    if thumb_file and os.path.exists(thumb_file): os.remove(thumb_file)
    bot.edit_message_text("✅ Download finished", chat, msg.message_id)
    live_progress.pop(chat, None)

# -------------------------
# AUTO-CLEANUP THREAD
# -------------------------
def cleanup_thread():
    while True:
        now = time.time()
        for f in os.listdir(TEMP_DIR):
            if f.endswith((".mp4", ".mp3")):
                fpath = os.path.join(TEMP_DIR, f)
                if now - os.path.getctime(fpath) > FILE_EXPIRY:
                    os.remove(fpath)
        time.sleep(300)

threading.Thread(target=cleanup_thread, daemon=True).start()

# -------------------------
# RUN BOT
# -------------------------
print("BOT STARTED")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
