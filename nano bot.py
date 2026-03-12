import telebot
import yt_dlp
import os
import sqlite3
import threading
import time

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"

ADMIN_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

queue = []

def save_user(uid):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    conn.commit()

@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send a link from:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\n\n"
        "⬇️ Bot downloads automatically."
    )

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def downloader(message):

    bot.reply_to(message,"📥 Added to download queue...")
    queue.append(message)

def worker():
    while True:
        if queue:
            msg = queue.pop(0)
            process(msg)
        time.sleep(1)

threading.Thread(target=worker, daemon=True).start()

def process(message):

    url = message.text
    status = bot.send_message(message.chat.id,"⏳ Downloading...")

    try:

        ydl_opts = {
            "format": "best",
            "outtmpl": "%(title)s.%(ext)s",
            "noplaylist": True,
            "retries": 10
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)
            file = ydl.prepare_filename(info)

        size = os.path.getsize(file)

        if size < 49000000:

            bot.send_video(message.chat.id, open(file,"rb"))

        else:

            bot.send_document(message.chat.id, open(file,"rb"))

        os.remove(file)

        bot.edit_message_text(
            "✅ Download completed!",
            message.chat.id,
            status.message_id
        )

    except:

        bot.edit_message_text(
            "❌ Download failed. Try another link.",
            message.chat.id,
            status.message_id
        )

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

    bot.send_message(message.chat.id,"✅ Broadcast sent.")

@bot.message_handler(commands=['reply'])
def reply_user(message):

    if message.chat.id != ADMIN_ID:
        return

    try:
        parts = message.text.split(" ",2)

        uid = int(parts[1])
        text = parts[2]

        bot.send_message(uid,text)

        bot.send_message(message.chat.id,"✅ Message sent.")

    except:

        bot.send_message(message.chat.id,"Usage:\n/reply USER_ID message")

while True:

    try:
        bot.infinity_polling(timeout=60,long_polling_timeout=60)

    except:
        time.sleep(5)
