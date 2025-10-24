import logging
import os

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🤖 CHATRIX BOT STARTING...")
print("=" * 60)

# Конфігурація
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID', '1385645772')
PORT = int(os.environ.get('PORT', 10000))

print(f"🔧 Configuration:")
print(f"   TOKEN: {TOKEN[:10] + '...' if TOKEN else 'NOT SET'}")
print(f"   ADMIN_ID: {ADMIN_ID}")
print(f"   PORT: {PORT}")

# Перевірка обов'язкових змінних
if not TOKEN:
    print("❌ CRITICAL: BOT_TOKEN not set!")
    print("💡 Please set BOT_TOKEN environment variable in Render dashboard")
    exit(1)

# Імпорт залежностей
try:
    print("📦 Importing dependencies...")
    from flask import Flask, request
    print("   ✅ Flask")
    
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    print("   ✅ python-telegram-bot")
    
    # Спроба імпорту бази даних
    try:
        from database_postgres import db
        print("   ✅ PostgreSQL database")
    except ImportError as e:
        print(f"   ⚠️ Database: {e}")
        # Заглушка для бази даних
        class DatabaseStub:
            def get_user(self, user_id): return None
            def add_user(self, user_id, username, first_name): 
                logger.info(f"📝 Added user: {user_id} - {first_name}")
                return True
            def get_users_count(self): return 0
            def get_statistics(self): return (0, 0, 0, [])
            def get_user_profile(self, user_id): return (None, False)
        db = DatabaseStub()
    
    print("✅ All dependencies imported successfully!")
    
except ImportError as e:
    print(f"❌ Failed to import dependencies: {e}")
    print("💡 Please check requirements.txt and rebuild")
    exit(1)

# Створення Flask додатку
app = Flask(__name__)

# Глобальні змінні
application = None
bot_initialized = False

# Проста команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logger.info(f"🆕 User {user.id} started the bot")
        
        # Додаємо користувача в базу
        db.add_user(user.id, user.username, user.first_name)
        
        await update.message.reply_text(
            f"👋 Вітаю, {user.first_name}!\n\n"
            f"💞 *Chatrix* — бот для знайомств\n\n"
            f"🆔 Ваш ID: `{user.id}`\n"
            f"📊 Користувачів у базі: {db.get_users_count()}\n\n"
            f"🎯 Оберіть дію з меню 👇",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Error in /start: {e}")
        await update.message.reply_text("❌ Сталася помилка. Спробуйте ще раз.")

# Ініціалізація бота
def init_bot():
    global application, bot_initialized
    
    if bot_initialized:
        return application
        
    try:
        print("🔄 Initializing bot...")
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("debug", start_command))
        
        # Ініціалізуємо
        application.initialize()
        
        # Встановлюємо вебхук
        WEBHOOK_URL = os.environ.get('WEBHOOK_URL', f"https://chatrix-bot-4m1p.onrender.com/webhook")
        application.bot.set_webhook(WEBHOOK_URL)
        
        bot_initialized = True
        print(f"✅ Bot initialized successfully!")
        print(f"🌐 Webhook: {WEBHOOK_URL}")
        
        return application
        
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        return None

# Маршрути Flask
@app.route('/')
def home():
    return "🤖 Chatrix Bot is running! Use /start in Telegram.", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    
    try:
        # Ініціалізуємо бота при першому запиті
        if not application:
            application = init_bot()
            if not application:
                return "Bot initialization failed", 500
        
        update_data = request.get_json()
        if not update_data:
            return "Empty data", 400
            
        update = Update.de_json(update_data, application.bot)
        application.process_update(update)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "Error", 500

@app.route('/init', methods=['GET'])
def initialize():
    """Ручна ініціалізація бота"""
    result = init_bot()
    if result:
        return "Bot initialized successfully", 200
    else:
        return "Bot initialization failed", 500

print("=" * 60)
print("✅ BOT INITIALIZATION COMPLETED!")
print("🤖 Server is ready to handle requests")
print("=" * 60)

# Ініціалізуємо бота при запуску
init_bot()

if __name__ == '__main__':
    print(f"🌐 Starting Flask server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)