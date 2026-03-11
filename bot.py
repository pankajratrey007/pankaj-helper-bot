import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"

bot = telebot.TeleBot(TOKEN)

video_cache = {}

# START
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Helper Bot\n\n"
        "Send a video link from YouTube / Instagram / TikTok."
    )

# WHEN USER SENDS LINK
@bot.message_handler(func=lambda m: "http" in m.text)
def get_qualities(message):

    url = message.text

    bot.send_message(message.chat.id, "🔎 Fetching video qualities...")

    ydl_opts = {'quiet': True}

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])

        markup = InlineKeyboardMarkup()

        added = set()

        for f in formats:

            height = f.get("height")

            if height and height not in added:

                added.add(height)

                btn = InlineKeyboardButton(
                    f"{height}p",
                    callback_data=f"{height}|{url}"
                )

                markup.add(btn)

        audio_btn = InlineKeyboardButton(
            "🎧 Audio MP3",
            callback_data=f"audio|{url}"
        )

        markup.add(audio_btn)

        bot.send_message(
            message.chat.id,
            "🎬 Choose quality:",
            reply_markup=markup
        )

    except:
        bot.send_message(message.chat.id, "❌ Could not read video.")

# DOWNLOAD
@bot.callback_query_handler(func=lambda call: True)
def download(call):

    quality, url = call.data.split("|")

    msg = bot.send_message(call.message.chat.id, "⏳ Downloading...")

    try:

        if quality == "audio":

            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": "audio.%(ext)s"
            }

        else:

            ydl_opts = {
                "format": f"bestvideo[height<={quality}]+bestaudio/best",
                "outtmpl": "video.%(ext)s"
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)

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
            "❌ Download failed.\nVideo may be too large for Telegram.",
            call.message.chat.id,
            msg.message_id
        )

bot.infinity_polling()
