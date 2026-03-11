import telebot
import yt_dlp
import os
import threading
import time

TOKEN = "8769882137:AAFACkzcXlGXVJA5ymMs4E7woW4DlEkBRww"

bot = telebot.TeleBot(TOKEN)

download_queue = []

# progress hook
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '')
        speed = d.get('_speed_str', '')
        print(f"Downloading {percent} at {speed}")

# worker system
def worker():
    while True:
        if download_queue:
            message = download_queue.pop(0)
            download_video(message)
        time.sleep(2)

threading.Thread(target=worker, daemon=True).start()

# start command
@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Helper Bot*\n\n"
        "Send a video link from:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter\n\n"
        "The bot will download it automatically.",
        parse_mode="Markdown"
    )

# detect links automatically
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def add_to_queue(message):

    bot.reply_to(message, "📥 Added to download queue...")
    download_queue.append(message)

# main download function
def download_video(message):

    url = message.text

    status = bot.send_message(message.chat.id, "⏳ Download starting...")

    try:

        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        filesize = os.path.getsize(filename) / (1024 * 1024)

        if filesize > 49:

            bot.edit_message_text(
                "⚠️ File too large for Telegram (limit about 50MB).",
                message.chat.id,
                status.message_id
            )

            os.remove(filename)
            return

        with open(filename, "rb") as video:

            bot.send_video(message.chat.id, video)

        bot.edit_message_text(
            "✅ Download completed!",
            message.chat.id,
            status.message_id
        )

        os.remove(filename)

    except Exception:

        bot.edit_message_text(
            "❌ Download failed.\nVideo may be restricted or unsupported.",
            message.chat.id,
            status.message_id
        )

bot.infinity_polling()
