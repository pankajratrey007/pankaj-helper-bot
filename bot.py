import telebot
import yt_dlp
import sqlite3
import threading
import os
import subprocess
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

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
        "Send a video link from:\n"
        "YouTube / Instagram / TikTok / Facebook"
    )

# LINK DETECT
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def select_quality(message):

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

# BUTTON CLICK
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    quality,url = call.data.split("|")

    queue.append((call.message.chat.id,url,quality))

    bot.send_message(call.message.chat.id,"📥 Added to queue")

# WORKER SYSTEM
def worker():

    while True:

        if queue:

            chat_id,url,quality = queue.pop(0)

            process(chat_id,url,quality)

        else:
            time.sleep(1)

# START 5 PARALLEL WORKERS
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
            "format":format_code.get(quality,"best"),
            "outtmpl":"video.%(ext)s",
            "retries":15,
            "fragment_retries":15,
            "geo_bypass":True,
            "nocheckcertificate":True,
            "progress_hooks":[progress_hook]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url,download=True)

            file = ydl.prepare_filename(info)

            site = info.get("extractor","unknown")

        bot.send_message(chat_id,f"🌐 Source detected: {site}")

        size = os.path.getsize(file)

        # SPLIT LARGE FILE
        if size > 1900000000:

            bot.send_message(chat_id,"📦 Splitting large file...")

            subprocess.call([
                "ffmpeg","-i",file,
                "-c","copy",
                "-map","0",
                "-segment_time","00:10:00",
                "-f","segment",
                "part_%03d.mp4"
            ])

            for f in os.listdir():

                if f.startswith("part_"):

                    bot.send_document(chat_id,open(f,"rb"))

                    os.remove(f)

        else:

            bot.send_document(chat_id,open(file,"rb"))

        os.remove(file)

        bot.edit_message_text(
            "✅ Download complete!",
            chat_id,
            status.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed. Try another link.",
            chat_id,
            status.message_id
        )

# BROADCAST
@bot.message_handler(commands=['broadcast'])
def broadcast(message):

    if message.chat.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast ","")

    cursor.execute("SELECT id FROM users")

    users = cursor.fetchall()

    for u in users:

        try:
            bot.send_message(u[0],text)
        except:
            pass

    bot.send_message(message.chat.id,"✅ Broadcast sent")

# RUN
while True:

    try:

        bot.infinity_polling(timeout=60,long_polling_timeout=60)

    except:
        time.sleep(5)
