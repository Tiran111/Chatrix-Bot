import logging
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TOKEN = os.environ.get('BOT_TOKEN')
URL = "https://chatrix-bot-4m1p.onrender.com"  # Твоя URL

# Глобальна змінна для бота
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        ['📝 Заповнити профіль', '👤 Мій профіль'],
        ['💕 Пошук анкет', '🏙️ По місту'],
        ['❤️ Хто мене лайкнув', '💌 Мої матчі'],
        ['🏆 Топ', "👨‍💼 Зв'язок з адміном"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n💞 *Chatrix* — бот для знайомств!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    responses = {
        "📝 Заповнити профіль": "📝 Заповнення профілю...",
        "👤 Мій профіль": "👤 Ваш профіль...", 
        "💕 Пошук анкет": "💕 Пошук анкет...",
        "🏙️ По місту": "🏙️ Пошук по місту...",
        "❤️ Хто мене лайкнув": "❤️ Перегляд лайків...",
        "💌 Мої матчі": "💌 Ваші матчі...",
        "🏆 Топ": "🏆 Топ користувачів...",
        "👨‍💼 Зв'язок з адміном": "👨‍💼 Зв'язок з адміном..."
    }
    
    response = responses.get(text, "❌ Команда не розпізнана")
    await update.message.reply_text(response)

@app.route('/')
def home():
    return "🤖 Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    if application is None:
        return "Bot not initialized", 500
        
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put_nowait(update)
    return 'ok'

@app.route('/set_webhook')
def set_webhook():
    """Встановити webhook"""
    global application
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Встановлюємо webhook
        webhook_url = f"{URL}/webhook"
        application.bot.set_webhook(webhook_url)
        
        logger.info(f"✅ Webhook встановлено: {webhook_url}")
        return f"Webhook set to: {webhook_url}"
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")
        return f"Error: {e}"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Запуск Flask сервера...")
    app.run(host='0.0.0.0', port=port, debug=False)