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

    btn1 = InlineKeyboardButton("📥 YouTube Video", callback_data="ytvideo")
    btn2 = InlineKeyboardButton("🎧 YouTube Audio", callback_data="ytaudio")
    btn3 = InlineKeyboardButton("📸 Instagram", callback_data="insta")
    btn4 = InlineKeyboardButton("📜 Help", callback_data="help")
    btn5 = InlineKeyboardButton("🌐 Website", url="https://example.com")
    btn6 = InlineKeyboardButton("💬 Support", url="https://t.me/yourusername")
    btn7 = InlineKeyboardButton("ℹ️ About", callback_data="about")

    markup.add(btn1, btn2)
    markup.add(btn3)
    markup.add(btn4, btn7)
    markup.add(btn5)
    markup.add(btn6)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to *Pankaj Helper Bot*\n\nSend a YouTube link anytime to download.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# BUTTON HANDLER
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):

    if call.data == "ytvideo":
        bot.send_message(call.message.chat.id,"📥 Send YouTube link to download video.")

    elif call.data == "ytaudio":
        bot.send_message(call.message.chat.id,"🎧 Send YouTube link to download MP3.")

    elif call.data == "insta":
        bot.send_message(call.message.chat.id,"📸 Instagram downloader coming soon.")

    elif call.data == "help":
        bot.send_message(call.message.chat.id,
        "📜 Commands\n\n"
        "/start\n"
        "/admin\n"
        "/users\n"
        "/broadcast message")

    elif call.data == "about":
        bot.send_message(call.message.chat.id,
        "🤖 Pankaj Helper Bot\nCreated by Pankaj\nRunning on Railway 🚂")

# YOUTUBE DOWNLOAD (MORE STABLE)
@bot.message_handler(func=lambda m: "youtu" in m.text.lower())
def download_video(message):

    url = message.text.strip()

    bot.reply_to(message,"⏳ Processing video...")

    ydl_opts = {
        'format': 'best[filesize<50M]',
        'noplaylist': True,
        'outtmpl': 'video.%(ext)s',
        'quiet': True
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)

        video = open(filename,'rb')

        bot.send_video(message.chat.id, video)

    except Exception as e:

        bot.reply_to(message,"❌ Download failed.\nVideo may be too large or restricted.")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(message):

    if message.from_user.id == OWNER_ID:

        bot.reply_to(message,
        "🔧 Admin Panel\n\n"
        "/users - show users\n"
        "/broadcast message")

    else:

        bot.reply_to(message,"❌ Not allowed")

# USER COUNT
@bot.message_handler(commands=['users'])
def user_count(message):

    if message.from_user.id == OWNER_ID:

        bot.reply_to(message,f"👥 Total users: {len(users)}")

# BROADCAST
@bot.message_handler(commands=['broadcast'])
def broadcast(message):

    if message.from_user.id == OWNER_ID:

        text = message.text.replace("/broadcast ","")

        for user in users:

            try:
                bot.send_message(user,text)
            except:
                pass

        bot.reply_to(message,"✅ Broadcast sent")

bot.infinity_polling()l
