import telebot
import yt_dlp
import os
import sqlite3
import threading
import time

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

# DATABASE
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(user_id,))
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
        "YouTube / Instagram / TikTok / Facebook / Twitter\n\n"
        "The bot will download automatically."
    )

# LINK DETECTION
@bot.message_handler(func=lambda message: message.text and "http" in message.text)
def add_queue(message):

    bot.reply_to(message,"📥 Added to download queue...")

    queue.append(message)

# WORKER
def worker():

    while True:

        if queue:

            message = queue.pop(0)

            download_video(message)

        time.sleep(2)

threading.Thread(target=worker,daemon=True).start()

# DOWNLOAD FUNCTION
def download_video(message):

    url = message.text

    status = bot.send_message(message.chat.id,"⏳ Download starting...")

    try:

        ydl_opts = {
            'format':'bestvideo[height<=720]+bestaudio/best',
            'outtmpl':'%(title)s.%(ext)s',
            'noplaylist':True,
            'quiet':True,
            'nocheckcertificate':True,
            'ignoreerrors':False,
            'retries':10,
            'fragment_retries':10
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)

        size = os.path.getsize(filename)/(1024*1024)

        if size < 50:

            with open(filename,"rb") as video:

                bot.send_video(message.chat.id,video)

        else:

            bot.send_message(
                message.chat.id,
                "📦 File larger than Telegram bot limit.\n\n"
                "Download from original link:\n"+url
            )

        os.remove(filename)

        bot.edit_message_text(
            "✅ Download completed!",
            message.chat.id,
            status.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed.\nThis website may block downloads.",
            message.chat.id,
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

    for user in users:

        try:
            bot.send_message(user[0],text)
        except:
            pass

    bot.send_message(message.chat.id,"✅ Broadcast sent.")

# ADMIN REPLY
@bot.message_handler(commands=['reply'])
def reply_user(message):

    if message.chat.id != ADMIN_ID:
        return

    try:

        parts = message.text.split(" ",2)

        user_id = int(parts[1])

        text = parts[2]

        bot.send_message(user_id,text)

        bot.send_message(message.chat.id,"✅ Message sent.")

    except:

        bot.send_message(message.chat.id,"Usage:\n/reply USER_ID message")

# AUTO RESTART
while True:
    try:
        bot.infinity_polling(timeout=60,long_polling_timeout=60)
    except Exception as e:
        print("Bot crashed, restarting...")
        time.sleep(5)
