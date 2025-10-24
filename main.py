import logging
import os

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🚀 БОТ ЗАПУСКАЄТЬСЯ...")
print("=" * 60)

# Перевірка залежностей
try:
    from flask import Flask, request
    print("✅ Flask успішно імпортовано")
    
    from telegram import Update
    from telegram.ext import Application, CommandHandler
    print("✅ python-telegram-bot успішно імпортовано")
    
    try:
        from database_postgres import db
        print("✅ База даних успішно імпортована")
    except ImportError:
        print("⚠️ База даних не імпортована - створюємо заглушку")
        class DatabaseStub:
            def get_user(self, user_id): return None
            def add_user(self, user_id, username, first_name): 
                print(f"📝 Додано користувача: {user_id} - {first_name}")
                return True
        db = DatabaseStub()
    
except ImportError as e:
    print(f"❌ Помилка імпорту: {e}")
    print("❌ БУДЬ ЛАСКА, ПЕРЕВІРТЕ pyproject.toml")
    exit(1)

# Конфігурація
TOKEN = os.environ.get('BOT_TOKEN', 'test_token')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '1385645772'))
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', "https://chatrix-bot-4m1p.onrender.com/webhook")

print(f"✅ Токен: {TOKEN[:10]}...")
print(f"✅ ADMIN_ID: {ADMIN_ID}")
print(f"✅ Порт: {PORT}")
print(f"✅ Вебхук: {WEBHOOK_URL}")

# Створення Flask додатку
app = Flask(__name__)

# Прості маршрути
@app.route('/')
def home():
    return "🤖 Chatrix Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"📩 Отримано вебхук: {data}")
        return "OK", 200
    except Exception as e:
        logger.error(f"❌ Помилка вебхука: {e}")
        return "Error", 500

# Проста команда /start
async def start_command(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n\n"
        f"💞 Chatrix Bot успішно запущено!\n"
        f"🆔 Ваш ID: {user.id}"
    )

# Ініціалізація бота
def init_bot():
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        application.initialize()
        application.bot.set_webhook(WEBHOOK_URL)
        print("✅ Бот успішно ініціалізовано!")
        return application
    except Exception as e:
        print(f"❌ Помилка ініціалізації бота: {e}")
        return None

print("=" * 60)
print("✅ ВСІ ЗАЛЕЖНОСТІ УСПІШНО ЗАВАНТАЖЕНО!")
print("🤖 СЕРВЕР ГОТОВИЙ ДО РОБОТИ")
print("=" * 60)

if __name__ == '__main__':
    # Ініціалізуємо бота
    bot_app = init_bot()
    
    # Запускаємо Flask сервер
    print(f"🌐 Запуск сервера на порті {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)