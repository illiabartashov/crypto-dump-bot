import time
import telebot
from config import TELEGRAM_TOKEN

ALLOWED_USERS = {5609621175}

def is_allowed(user_id):
    return user_id in ALLOWED_USERS


bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    if not is_allowed(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Доступ заборонено")
        return

    bot.send_message(message.chat.id, "Бот активний")

@bot.message_handler(commands=['status'])
def status(message):
    if not is_allowed(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Доступ заборонено")
        return

    bot.send_message(message.chat.id, "Все працює")

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
