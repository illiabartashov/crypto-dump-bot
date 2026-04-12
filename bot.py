import telebot
from config import TELEGRAM_TOKEN, CHAT_ID

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот працює! Сканую ринок 24/7 🔍")

@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, "Сканер активний. Сигнали надходитимуть автоматично 📡")

if __name__ == "__main__":
    print("Telegram bot is running...")
    bot.infinity_polling()