import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAENSY3nUv-fE3beMDQpOCmxTaEg1ffeaYw"
OWNER_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

# START MENU
@bot.message_handler(commands=['start'])
def start(message):

    markup = InlineKeyboardMarkup()

    btn1 = InlineKeyboardButton("📜 Help", callback_data="help")
    btn2 = InlineKeyboardButton("📥 YouTube Download", callback_data="download")
    btn3 = InlineKeyboardButton("ℹ️ About", callback_data="about")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Helper Bot\n\nSend a YouTube link to download video 🎬",
        reply_markup=markup
    )

# HELP BUTTON
@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_menu(call):

    bot.edit_message_text(
        "📜 Commands:\n\n"
        "/start - Start bot\n"
        "/admin - Admin panel\n\n"
        "Simply send a YouTube link to download the video.",
        call.message.chat.id,
        call.message.message_id
    )

# ABOUT BUTTON
@bot.callback_query_handler(func=lambda call: call.data == "about")
def about(call):

    bot.edit_message_text(
        "🤖 Pankaj Helper Bot\n"
        "Created by Pankaj\n"
        "Hosted on Railway 🚂",
        call.message.chat.id,
        call.message.message_id
    )

# DOWNLOAD BUTTON
@bot.callback_query_handler(func=lambda call: call.data == "download")
def download_info(call):

    bot.send_message(
        call.message.chat.id,
        "📥 Send a YouTube video link and I will download it for you."
    )

# YOUTUBE LINK DETECTOR
@bot.message_handler(func=lambda m: "youtu" in m.text)
def download_video(message):

    url = message.text

    bot.reply_to(message, "⏳ Downloading video...")

    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video.%(ext)s'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        video = open(filename, 'rb')
        bot.send_video(message.chat.id, video)

    except:
        bot.reply_to(message, "❌ Failed to download video.")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(message):

    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "🔧 Admin panel active.\nYou control the bot.")
    else:
        bot.reply_to(message, "❌ You are not allowed.")

bot.infinity_polling()
