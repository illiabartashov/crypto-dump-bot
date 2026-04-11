import telebot
from config import TELEGRAM_TOKEN

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот працює!")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
