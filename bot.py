import telebot
import yt_dlp
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"

bot = telebot.TeleBot(TOKEN)

# START
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Helper Bot\n\n"
        "Send a video link from:\n"
        "YouTube / Instagram / TikTok"
    )

# GET VIDEO QUALITIES
@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def get_video_info(message):

    url = message.text

    bot.send_message(message.chat.id, "🔎 Checking video...")

    try:

        ydl_opts = {
            'quiet': True,
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])

        markup = InlineKeyboardMarkup()
        added = set()

        for f in formats:

            height = f.get("height")

            if height and height not in added and height <= 720:

                added.add(height)

                markup.add(
                    InlineKeyboardButton(
                        f"{height}p",
                        callback_data=f"{height}|{url}"
                    )
                )

        markup.add(
            InlineKeyboardButton(
                "🎧 Audio",
                callback_data=f"audio|{url}"
            )
        )

        bot.send_message(
            message.chat.id,
            "🎬 Select quality:",
            reply_markup=markup
        )

    except Exception as e:

        bot.send_message(
            message.chat.id,
            "❌ Could not read video.\nTry another link."
        )

# DOWNLOAD
@bot.callback_query_handler(func=lambda call: True)
def download(call):

    quality, url = call.data.split("|")

    msg = bot.send_message(call.message.chat.id, "⏳ Downloading...")

    try:

        if quality == "audio":

            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': 'audio.%(ext)s'
            }

        else:

            ydl_opts = {
                'format': f'bestvideo[height<={quality}]+bestaudio/best',
                'outtmpl': 'video.%(ext)s'
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        size = os.path.getsize(filename) / (1024 * 1024)

        if size > 49:

            bot.edit_message_text(
                "⚠️ File too large for Telegram (over 50MB).",
                call.message.chat.id,
                msg.message_id
            )

            return

        file = open(filename, "rb")

        if quality == "audio":
            bot.send_audio(call.message.chat.id, file)
        else:
            bot.send_video(call.message.chat.id, file)

        bot.edit_message_text(
            "✅ Download complete!",
            call.message.chat.id,
            msg.message_id
        )

    except Exception as e:

        bot.edit_message_text(
            "❌ Download failed.\nVideo may be restricted.",
            call.message.chat.id,
            msg.message_id
        )

bot.infinity_polling()
