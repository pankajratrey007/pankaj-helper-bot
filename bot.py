import telebot
import yt_dlp
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAENSY3nUv-fE3beMDQpOCmxTaEg1ffeaYw"
OWNER_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

users = set()

# START MENU
@bot.message_handler(commands=['start'])
def start(message):

    users.add(message.chat.id)

    markup = InlineKeyboardMarkup()

    btn1 = InlineKeyboardButton("📥 Download Video", callback_data="video")
    btn2 = InlineKeyboardButton("🎧 Download Audio", callback_data="audio")
    btn3 = InlineKeyboardButton("📜 Help", callback_data="help")
    btn4 = InlineKeyboardButton("ℹ️ About", callback_data="about")

    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3, btn4)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Helper Bot*\n\nSend a YouTube link to download.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# BUTTON HANDLER
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    if call.data == "video":

        bot.send_message(call.message.chat.id,
        "📥 Send a YouTube link to download video.")

    elif call.data == "audio":

        bot.send_message(call.message.chat.id,
        "🎧 Send a YouTube link to download MP3.")

    elif call.data == "help":

        bot.send_message(call.message.chat.id,
        "📜 Commands:\n/start\n/admin\n/broadcast\n/users")

    elif call.data == "about":

        bot.send_message(call.message.chat.id,
        "🤖 Pankaj Helper Bot\nCreated by Pankaj")

# YOUTUBE VIDEO DOWNLOAD
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

        bot.reply_to(message, "❌ Download failed.")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(message):

    if message.from_user.id == OWNER_ID:

        bot.reply_to(message,
        "🔧 Admin Panel\n\n"
        "/users - user count\n"
        "/broadcast message")

# USER COUNT
@bot.message_handler(commands=['users'])
def user_count(message):

    if message.from_user.id == OWNER_ID:

        bot.reply_to(message,
        f"👥 Total users: {len(users)}")

# BROADCAST MESSAGE
@bot.message_handler(commands=['broadcast'])
def broadcast(message):

    if message.from_user.id == OWNER_ID:

        text = message.text.replace("/broadcast ", "")

        for user in users:

            try:

                bot.send_message(user, text)

            except:

                pass

        bot.reply_to(message, "✅ Message sent.")

bot.infinity_polling()
