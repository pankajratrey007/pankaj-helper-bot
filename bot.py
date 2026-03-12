import telebot
import yt_dlp
import os
import sqlite3
import time

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"
ADMIN_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(user_id,))
    conn.commit()

@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send any video link from:\n"
        "YouTube / Instagram / TikTok / Facebook / Twitter"
    )

@bot.message_handler(func=lambda message: message.text and "http" in message.text)
def download(message):

    url = message.text

    status = bot.send_message(message.chat.id,"⏳ Downloading...")

    try:

        ydl_opts = {
            "format": "best",
            "outtmpl": "%(title)s.%(ext)s",
            "noplaylist": True,
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
                "⚠️ File larger than Telegram bot limit.\n\nDownload here:\n"+url
            )

        os.remove(filename)

        bot.edit_message_text(
            "✅ Download completed!",
            message.chat.id,
            status.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed.\nTry another link.",
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

    for user in users:

        try:
            bot.send_message(user[0],text)
        except:
            pass

    bot.send_message(message.chat.id,"✅ Broadcast sent.")

while True:
    try:
        bot.infinity_polling(timeout=60,long_polling_timeout=60)
    except:
        print("Restarting bot...")
        time.sleep(5)
