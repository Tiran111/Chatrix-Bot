import logging
import os

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("==========================================")
print("🤖 CHATRIX BOT - STARTING...")
print("==========================================")

# Конфігурація
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID', '1385645772')
PORT = int(os.environ.get('PORT', 10000))

print(f"TOKEN: {TOKEN[:10] + '...' if TOKEN else 'NOT SET'}")
print(f"ADMIN_ID: {ADMIN_ID}")
print(f"PORT: {PORT}")

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    print("💡 Set BOT_TOKEN in Render environment variables")
    exit(1)

# Імпорт залежностей
try:
    from flask import Flask, request
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    print("✅ Dependencies imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Створення Flask додатку
app = Flask(__name__)

# Глобальні змінні
application = None

# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n"
        f"🆔 Ваш ID: {user.id}\n\n"
        f"💞 Chatrix Bot працює!",
        parse_mode='Markdown'
    )

# Ініціалізація бота
def init_bot():
    global application
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        application.initialize()
        
        WEBHOOK_URL = os.environ.get('WEBHOOK_URL', "https://chatrix-bot-4m1p.onrender.com/webhook")
        application.bot.set_webhook(WEBHOOK_URL)
        
        print(f"✅ Bot initialized - Webhook: {WEBHOOK_URL}")
        return application
    except Exception as e:
        print(f"❌ Bot init error: {e}")
        return None

# Маршрути Flask
@app.route('/')
def home():
    return "🤖 Chatrix Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    try:
        if not application:
            application = init_bot()
        update_data = request.get_json()
        if update_data:
            update = Update.de_json(update_data, application.bot)
            application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

print("==========================================")
print("✅ BOT READY - Starting server...")
print("==========================================")

# Ініціалізація при запуску
init_bot()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)