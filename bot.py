import telebot
import yt_dlp
import os
import threading

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"

bot = telebot.TeleBot(TOKEN)

# download queue
queue = []

# progress bar
def progress_hook(d):

    if d['status'] == 'downloading':

        percent = d['_percent_str']

        bot.send_chat_action(chat_id, 'upload_video')

# worker thread
def worker():

    while True:

        if queue:

            message = queue.pop(0)

            download_video(message)

threading.Thread(target=worker, daemon=True).start()

# start command
@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Helper Bot\n\n"
        "Send a video link from:\n"
        "YouTube\nInstagram\nTikTok\nFacebook\nTwitter/X"
    )

# auto detect links
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_link(message):

    bot.reply_to(message, "📥 Added to download queue...")

    queue.append(message)

# download function
def download_video(message):

    url = message.text

    msg = bot.send_message(message.chat.id, "⏳ Downloading...")

    try:

        ydl_opts = {
            'format': 'best[height<=720]',
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)

        size = os.path.getsize(filename) / (1024 * 1024)

        if size > 49:

            bot.send_message(
                message.chat.id,
                "⚠️ File larger than Telegram limit (50MB)."
            )

            os.remove(filename)
            return

        video = open(filename, "rb")

        bot.send_video(message.chat.id, video)

        bot.edit_message_text(
            "✅ Download complete!",
            message.chat.id,
            msg.message_id
        )

        os.remove(filename)

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed.\nTry another link.",
            message.chat.id,
            msg.message_id
        )

bot.infinity_polling()
