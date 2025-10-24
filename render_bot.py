import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація
TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"

async def start(update: Update, context):
    """Обробник команди /start"""
    await update.message.reply_text(
        "👋 Вітаю! Я Chatrix Bot - бот для знайомств! 🎉\n\n"
        "💕 Можливості:\n"
        "• Пошук анкет\n"
        "• Лайки та матчі\n"
        "• Топ користувачів\n"
        "• Пошук за містом\n\n"
        "🎯 Почнімо знайомство!"
    )

async def handle_message(update: Update, context):
    """Обробник текстових повідомлень"""
    await update.message.reply_text(
        "🔧 Основний функціонал завантажується...\n"
        "Спробуйте команду /start"
    )

async def main():
    """Головна функція бота"""
    try:
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Встановлюємо вебхук
        await application.initialize()
        await application.bot.set_webhook(WEBHOOK_URL)
        await application.start()
        
        logger.info("✅ Бот успішно запущено!")
        logger.info(f"🌐 Вебхук встановлено: {WEBHOOK_URL}")
        
        # Чекаємо безкінечно
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}")
        raise

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Запуск Chatrix Bot на Render...")
    print("=" * 50)
    asyncio.run(main())