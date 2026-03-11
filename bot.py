import telebot
import yt_dlp
import os
import threading
import time

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"
ADMIN_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

queue = []

# PROGRESS MESSAGE
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '')
        speed = d.get('_speed_str', '')
        print(f"Downloading {percent} at {speed}")

# WORKER
def worker():
    while True:
        if queue:
            message = queue.pop(0)
            download_video(message)
        time.sleep(1)

threading.Thread(target=worker, daemon=True).start()

# START
@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Downloader Bot\n\n"
        "Send any link from:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\n\n"
        "The bot will download automatically."
    )

# USER SEND LINK
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def add_queue(message):

    bot.reply_to(message, "📥 Added to queue. Download starting soon...")
    queue.append(message)

# DOWNLOAD
def download_video(message):

    url = message.text

    status = bot.send_message(message.chat.id, "⏳ Downloading...")

    try:

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'progress_hooks': [progress_hook]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        size = os.path.getsize(filename) / (1024 * 1024)

        if size < 50:

            with open(filename, "rb") as v:
                bot.send_video(message.chat.id, v)

            bot.edit_message_text(
                "✅ Download complete!",
                message.chat.id,
                status.message_id
            )

        else:

            bot.edit_message_text(
                "⚠️ File too large for Telegram.\n\n"
                "Download it here:",
                message.chat.id,
                status.message_id
            )

            bot.send_message(message.chat.id, url)

        os.remove(filename)

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed. Try another link.",
            message.chat.id,
            status.message_id
        )

# ADMIN CHAT
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_ID)
def forward_user(message):

    bot.forward_message(
        ADMIN_ID,
        message.chat.id,
        message.message_id
    )

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID)
def reply_admin(message):

    if message.reply_to_message:
        user_id = message.reply_to_message.forward_from.id
        bot.send_message(user_id, message.text)

bot.infinity_polling()
