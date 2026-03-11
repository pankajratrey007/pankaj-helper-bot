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

    help_btn = InlineKeyboardButton("📜 Help", callback_data="help")
    download_btn = InlineKeyboardButton("📥 Download YouTube", callback_data="download")
    about_btn = InlineKeyboardButton("ℹ️ About", callback_data="about")

    markup.add(help_btn)
    markup.add(download_btn)
    markup.add(about_btn)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Helper Bot*\n\nSend a YouTube link to download 🎬",
        parse_mode="Markdown",
        reply_markup=markup
    )

# BUTTON HANDLER
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    if call.data == "help":

        bot.send_message(
            call.message.chat.id,
            "📜 Commands:\n\n"
            "/start - Open menu\n"
            "/admin - Admin panel\n\n"
            "Send a YouTube link to download video."
        )

    elif call.data == "download":

        bot.send_message(
            call.message.chat.id,
            "📥 Send a YouTube video link and I will download it."
        )

    elif call.data == "about":

        bot.send_message(
            call.message.chat.id,
            "🤖 Pankaj Helper Bot\nCreated by Pankaj\nHosted on Railway 🚂"
        )

# YOUTUBE DOWNLOAD
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

    except Exception as e:
        bot.reply_to(message, "❌ Failed to download video.")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(message):

    if message.from_user.id == OWNER_ID:

        bot.reply_to(
            message,
            "🔧 Admin Panel\n\n"
            "Bot is running correctly ✅"
        )

    else:

        bot.reply_to(message, "❌ You are not allowed.")

bot.infinity_polling()
