import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAGVvBrpI32V6z2tc5o28L8ybV2peJ_6mug"
OWNER_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

# START MENU
@bot.message_handler(commands=['start'])
def start(message):

    markup = InlineKeyboardMarkup()

    btn1 = InlineKeyboardButton("📥 YouTube Download", callback_data="yt")
    btn2 = InlineKeyboardButton("📸 Instagram Download", callback_data="insta")
    btn3 = InlineKeyboardButton("🌐 Website", url="https://pankajratrey007.github.io/pankaj-helper-bot")
    btn4 = InlineKeyboardButton("💬 Support", url="https://t.me/Pankajratrey007")
    btn5 = InlineKeyboardButton("ℹ️ About", callback_data="about")

    markup.add(btn1, btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Helper Bot*\n\nChoose an option below.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# BUTTON HANDLER
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    if call.data == "yt":
        bot.send_message(call.message.chat.id,"📥 Send a YouTube link to download.")

    elif call.data == "insta":
        bot.send_message(call.message.chat.id,"📸 Send an Instagram video link.")

    elif call.data == "about":
        bot.send_message(call.message.chat.id,"🤖 Pankaj Helper Bot\nCreated by Pankaj")

# YOUTUBE DOWNLOAD
@bot.message_handler(func=lambda m: "youtu" in m.text.lower())
def yt_download(message):

    url = message.text

    bot.reply_to(message,"⏳ Downloading video...")

    ydl_opts = {
        'format': 'best[filesize<50M]',
        'outtmpl': 'video.%(ext)s'
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        video = open(filename,'rb')

        bot.send_video(message.chat.id,video)

    except:
        bot.reply_to(message,"❌ Download failed")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(message):

    if message.from_user.id == OWNER_ID:
        bot.reply_to(message,"✅ Admin panel active")

bot.infinity_polling()
