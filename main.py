import logging
import os
import time
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import Conflict

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TOKEN = os.environ.get('BOT_TOKEN')

@app.route('/')
def home():
    return "🤖 Chatrix Bot is running!"

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

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    if isinstance(error, Conflict):
        logger.warning("⚠️ Конфлікт - зупиняємо бота")
        # Зупиняємо бота при конфлікті
        if context.application.running:
            await context.application.stop()
        return
    logger.error(f"❌ Помилка: {error}")

def main():
    logger.info("🔄 Очікування 30 секунд перед запуском...")
    time.sleep(30)  # Чекаємо, поки можливі інші процеси зупиняться
    
    logger.info("🚀 Запуск бота...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
        application.add_error_handler(error_handler)
        
        def run_flask():
            port = int(os.environ.get('PORT', 10000))
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
        import threading
        threading.Thread(target=run_flask, daemon=True).start()
        
        logger.info("✅ Бот запущено!")
        application.run_polling(drop_pending_updates=True)
        
    except Conflict:
        logger.error("🚫 Конфлікт - бот вже запущений деінде")
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")

if __name__ == "__main__":
    main()