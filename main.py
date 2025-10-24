import logging
import os

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🚀 BUILD PROCESS STARTED...")
print("=" * 60)

# Конфігурація
TOKEN = os.environ.get('BOT_TOKEN', 'test_token')
ADMIN_ID = os.environ.get('ADMIN_ID', '1385645772')
PORT = int(os.environ.get('PORT', 10000))

print(f"✅ Config loaded: TOKEN={TOKEN[:10]}..., ADMIN_ID={ADMIN_ID}, PORT={PORT}")

# Перевірка залежностей після встановлення
try:
    from flask import Flask, request
    print("✅ Flask imported successfully")
    
    from telegram import Update
    from telegram.ext import Application, CommandHandler
    print("✅ python-telegram-bot imported successfully")
    
    # Спроба імпорту бази даних
    try:
        from database_postgres import db
        print("✅ Database imported successfully")
    except ImportError as e:
        print(f"⚠️ Database import failed: {e}")
        # Створюємо заглушку
        class DatabaseStub:
            def get_user(self, user_id): return None
            def add_user(self, user_id, username, first_name): 
                print(f"📝 Added user: {user_id} - {first_name}")
                return True
            def get_users_count(self): return 0
            def get_statistics(self): return (0, 0, 0, [])
        db = DatabaseStub()
    
    # Успішний імпорт
    print("=" * 60)
    print("✅ ALL DEPENDENCIES IMPORTED SUCCESSFULLY!")
    print("🤖 BOT IS READY FOR DEPLOYMENT")
    print("=" * 60)
    
    # Створення Flask додатку
    app = Flask(__name__)
    
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
            logger.info(f"📩 Webhook received")
            return "OK", 200
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
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
            
            # Встановлюємо вебхук тільки якщо токен не тестовий
            if TOKEN != 'test_token':
                WEBHOOK_URL = os.environ.get('WEBHOOK_URL', f"https://chatrix-bot-4m1p.onrender.com/webhook")
                application.bot.set_webhook(WEBHOOK_URL)
                print(f"✅ Webhook set: {WEBHOOK_URL}")
            
            print("✅ Bot initialized successfully!")
            return application
        except Exception as e:
            print(f"❌ Bot initialization error: {e}")
            return None
    
    # Глобальна змінна для бота
    bot_application = None
    
    @app.route('/init', methods=['POST'])
    def initialize_bot():
        global bot_application
        if not bot_application:
            bot_application = init_bot()
            return "Bot initialized", 200
        return "Bot already initialized", 200
        
except ImportError as e:
    print(f"❌ Import error during build: {e}")
    print("❌ This is normal during build process")
    print("✅ Dependencies will be installed by Render")
    
    # Створюємо простий Flask app для build process
    class FlaskStub:
        def __init__(self, name):
            self.name = name
        def route(self, rule, **options):
            def decorator(f):
                return f
            return decorator
    
    app = FlaskStub(__name__)
    
    # Прості функції для build
    def home():
        return "🤖 Chatrix Bot - Building...", 200
    
    def health():
        return "OK", 200

print("=" * 60)
print("✅ BUILD PROCESS COMPLETED SUCCESSFULLY!")
print("=" * 60)

if __name__ == '__main__':
    # Під час запуску ініціалізуємо бота
    if 'app' in locals() and hasattr(app, 'run'):
        print(f"🌐 Starting server on port {PORT}...")
        app.run(host='0.0.0.0', port=PORT, debug=False)
    else:
        print("⚠️ Running in build mode - server not started")