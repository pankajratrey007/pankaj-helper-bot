import telebot
import yt_dlp
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"

bot = telebot.TeleBot(TOKEN)

last_request = {}

# START
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Helper Bot*\n\n"
        "Send a video link from:\n"
        "YouTube / Instagram / TikTok / Facebook\n\n"
        "Then choose download quality.",
        parse_mode="Markdown"
    )

# LINK DETECTION
@bot.message_handler(func=lambda m: "http" in m.text)
def ask_quality(message):

    user = message.from_user.id

    # simple anti spam
    if user in last_request and time.time() - last_request[user] < 5:
        bot.reply_to(message, "⏳ Please wait a few seconds before another request.")
        return

    last_request[user] = time.time()

    url = message.text

    markup = InlineKeyboardMarkup()

    btn1 = InlineKeyboardButton("📹 360p", callback_data=f"360|{url}")
    btn2 = InlineKeyboardButton("🎬 720p", callback_data=f"720|{url}")
    btn3 = InlineKeyboardButton("🎧 MP3", callback_data=f"audio|{url}")

    markup.add(btn1, btn2)
    markup.add(btn3)

    bot.send_message(
        message.chat.id,
        "📥 Choose download quality:",
        reply_markup=markup
    )

# DOWNLOAD SYSTEM
@bot.callback_query_handler(func=lambda call: True)
def download(call):

    quality, url = call.data.split("|")

    bot.send_message(call.message.chat.id, "⏳ Download started...")

    try:

        if quality == "audio":

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': 'audio.%(ext)s'
            }

        elif quality == "360":

            ydl_opts = {
                'format': 'bestvideo[height<=360]+bestaudio/best',
                'outtmpl': 'video.%(ext)s'
            }

        else:

            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio/best',
                'outtmpl': 'video.%(ext)s'
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)

        file = open(filename, "rb")

        if quality == "audio":
            bot.send_audio(call.message.chat.id, file)
        else:
            bot.send_video(call.message.chat.id, file)

        bot.send_message(call.message.chat.id, "✅ Download complete!")

    except Exception as e:

        bot.send_message(
            call.message.chat.id,
            "❌ Download failed.\nFile may be too large or restricted."
        )

bot.infinity_polling()
