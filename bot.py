import telebot
import yt_dlp
import os
import sqlite3
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

def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(user_id,))
    conn.commit()

# START
@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Downloader Bot*\n\n"
        "Send video link from:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\n\n"
        "Then choose quality.",
        parse_mode="Markdown"
    )

# LINK DETECTION
@bot.message_handler(func=lambda message: message.text and "http" in message.text.lower())
def ask_quality(message):

    url = message.text

    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton("360p", callback_data=f"360|{url}"),
        InlineKeyboardButton("720p", callback_data=f"720|{url}")
    )

    markup.add(
        InlineKeyboardButton("1080p", callback_data=f"1080|{url}")
    )

    markup.add(
        InlineKeyboardButton("MP3", callback_data=f"audio|{url}")
    )

    bot.send_message(
        message.chat.id,
        "🎬 Choose download quality:",
        reply_markup=markup
    )

# DOWNLOAD
@bot.callback_query_handler(func=lambda call: True)
def download(call):

    quality, url = call.data.split("|")

    status = bot.send_message(call.message.chat.id,"⏳ Downloading...")

    try:

        if quality == "audio":

            ydl_opts = {
                'format':'bestaudio',
                'outtmpl':'audio.%(ext)s'
            }

        elif quality == "360":

            ydl_opts = {
                'format':'bestvideo[height<=360]+bestaudio/best',
                'outtmpl':'video.%(ext)s'
            }

        elif quality == "720":

            ydl_opts = {
                'format':'bestvideo[height<=720]+bestaudio/best',
                'outtmpl':'video.%(ext)s'
            }

        else:

            ydl_opts = {
                'format':'bestvideo[height<=1080]+bestaudio/best',
                'outtmpl':'video.%(ext)s'
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        size = os.path.getsize(filename)/(1024*1024)

        if size < 50:

            with open(filename,'rb') as file:

                if quality == "audio":
                    bot.send_audio(call.message.chat.id,file)
                else:
                    bot.send_video(call.message.chat.id,file)

        else:

            bot.send_message(
                call.message.chat.id,
                "⚠️ File too large for Telegram (50MB limit).\n\nDownload from original link:\n"+url
            )

        os.remove(filename)

        bot.edit_message_text(
            "✅ Download completed!",
            call.message.chat.id,
            status.message_id
        )

    except:

        bot.edit_message_text(
            "❌ Download failed. Try another link.",
            call.message.chat.id,
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
