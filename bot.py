import time
import telebot
from config import TELEGRAM_TOKEN

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот працює! Сканую ринок 24/7 🔍")

@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, "Сканер активний. Сигнали надходитимуть автоматично 📡")

def run_bot():
    print("Telegram bot is running...")

    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)  # пауза перед повтором


if __name__ == "__main__":
    run_bot()
