import telebot
import yt_dlp
import sqlite3
import threading
import os
import subprocess
import time

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

# DOWNLOAD QUEUE
queue = []

# START
@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send video link from:\n"
        "YouTube / Instagram / TikTok / Facebook\n\n"
        "Choose quality after sending link."
    )

# LINK HANDLER
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def ask_quality(message):

    url = message.text

    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton("360p", callback_data=f"360|{url}"),
        telebot.types.InlineKeyboardButton("720p", callback_data=f"720|{url}"),
        telebot.types.InlineKeyboardButton("1080p", callback_data=f"1080|{url}")
    )

    bot.send_message(message.chat.id,"Select quality:", reply_markup=markup)

# QUALITY SELECT
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    q,url = call.data.split("|")

    queue.append((call.message.chat.id,url,q))

    bot.edit_message_text(
        "📥 Added to queue...",
        call.message.chat.id,
        call.message.message_id
    )

# WORKER
def worker():

    while True:

        if queue:

            chat_id,url,quality = queue.pop(0)

            process(chat_id,url,quality)

        time.sleep(1)

threading.Thread(target=worker,daemon=True).start()

# DOWNLOAD PROCESS
def process(chat_id,url,quality):

    status = bot.send_message(chat_id,"⏳ Downloading...")

    try:

        format_code = {
            "360":"18",
            "720":"22",
            "1080":"137+140"
        }

        ydl_opts = {
            "format": format_code.get(quality,"best"),
            "outtmpl":"video.%(ext)s",
            "retries":10
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            file = ydl.prepare_filename(info)

        size = os.path.getsize(file)

        # SPLIT LARGE FILES
        if size > 1900000000:

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
            "❌ Download failed",
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

    for u in cursor.fetchall():

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
