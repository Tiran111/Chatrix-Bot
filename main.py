import logging
import os
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

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

@app.route('/health')
def health():
    return "OK", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    user = update.effective_user
    
    # Головне меню
    keyboard = [
        ['📝 Заповнити профіль', '👤 Мій профіль'],
        ['💕 Пошук анкет', '🏙️ По місту'],
        ['❤️ Хто мене лайкнув', '💌 Мої матчі'],
        ['🏆 Топ', "👨‍💼 Зв'язок з адміном"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n\n"
        f"💞 *Chatrix* — бот для знайомств!\n\n"
        f"🎯 Оберіть дію з меню:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник всіх текстових повідомлень"""
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"📨 Повідомлення від {user.first_name}: '{text}'")
    
    # Відповіді на кнопки меню
    responses = {
        "📝 Заповнити профіль": "📝 Розділ заповнення профілю!",
        "👤 Мій профіль": "👤 Тут буде ваш профіль",
        "💕 Пошук анкет": "💕 Шукаємо анкети для вас...",
        "🏙️ По місту": "🏙️ Введіть назву міста для пошуку",
        "❤️ Хто мене лайкнув": "❤️ Перевіряємо ваші лайки...", 
        "💌 Мої матчі": "💌 Завантажуємо ваші матчі...",
        "🏆 Топ": "🏆 Завантажуємо топ користувачів...",
        "👨‍💼 Зв'язок з адміном": "👨‍💼 Для зв'язку з адміністратором напишіть @admin"
    }
    
    if text in responses:
        await update.message.reply_text(responses[text])
    else:
        await update.message.reply_text(
            "🤖 Використовуйте кнопки меню для навігації. "
            "Якщо меню зникло, напишіть /start"
        )

def main():
    logger.info("🚀 Запуск Chatrix Bot...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники - ВАЖЛИВО: спочатку команди, потім текст
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
        
        # Flask для Render
        def run_flask():
            port = int(os.environ.get('PORT', 10000))
            logger.info(f"🌐 Flask запущено на порті {port}")
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
        import threading
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        logger.info("✅ Бот успішно запущений!")
        application.run_polling(
            drop_pending_updates=True,
            timeout=10
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску: {e}")

if __name__ == "__main__":
    main()