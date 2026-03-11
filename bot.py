import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8769882137:AAENSY3nUv-fE3beMDQpOCmxTaEg1ffeaYw"
OWNER_ID = 8274612882

bot = telebot.TeleBot(TOKEN)

# START COMMAND
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()

    btn1 = InlineKeyboardButton("📜 Help", callback_data="help")
    btn2 = InlineKeyboardButton("🌐 Website", url="https://example.com")
    btn3 = InlineKeyboardButton("📥 Downloader", callback_data="download")
    btn4 = InlineKeyboardButton("ℹ️ About", callback_data="about")

    markup.add(btn1, btn2)
    markup.add(btn3)
    markup.add(btn4)

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Pankaj Helper Bot\nChoose an option below:",
        reply_markup=markup
    )

# HELP BUTTON
@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_menu(call):
    bot.edit_message_text(
        "📜 Commands:\n"
        "/start - Start bot\n"
        "/help - Help menu\n"
        "/about - About bot\n"
        "/download - Download videos",
        call.message.chat.id,
        call.message.message_id
    )

# ABOUT BUTTON
@bot.callback_query_handler(func=lambda call: call.data == "about")
def about_bot(call):
    bot.edit_message_text(
        "🤖 Pankaj Helper Bot\nCreated by Pankaj.\nHosted on Railway.",
        call.message.chat.id,
        call.message.message_id
    )

# DOWNLOAD COMMAND
@bot.message_handler(commands=['download'])
def downloader(message):
    bot.reply_to(message, "📥 Send a YouTube link to download.")

# ADMIN PANEL (ONLY YOU CAN USE)
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "🔧 Admin panel active. You control the bot.")
    else:
        bot.reply_to(message, "❌ You are not allowed to use this command.")

bot.infinity_polling()
