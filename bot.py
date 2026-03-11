import telebot
import yt_dlp
import os
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"
ADMIN_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

# DATABASE
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
conn.commit()

# SAVE USER
def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(user_id,))
    conn.commit()

# START COMMAND
@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send any video link from:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\n\n"
        "Then choose download quality."
    )

# USER SEND LINK
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
        "Choose download quality:",
        reply_markup=markup
    )

# DOWNLOAD
@bot.callback_query_handler(func=lambda call: True)
def download(call):

    quality, url = call.data.split("|")

    msg = bot.send_message(call.message.chat.id,"⏳ Downloading...")

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
                "⚠️ File too large for Telegram.\nDownload from original link:\n"+url
            )

        os.remove(filename)

        bot.edit_message_text(
            "✅ Download complete",
            call.message.chat.id,
            msg.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed. Try another link.",
            call.message.chat.id,
            msg.message_id
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

# AUTO RESTART (fix bot stop problem)
while True:
    try:
        bot.infinity_polling(timeout=60,long_polling_timeout=60)
    except Exception as e:
        print("Bot crashed, restarting...")
