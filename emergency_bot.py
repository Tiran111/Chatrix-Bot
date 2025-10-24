import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"

async def start(update: Update, context):
    """Простий старт"""
    user = update.effective_user
    logger.info(f"🆕 Користувач {user.id} викликав /start")
    
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n"
        f"🆔 Ваш ID: {user.id}\n"
        "✅ Бот працює!\n\n"
        "🔧 Статус: Екстрений режим"
    )

async def echo(update: Update, context):
    """Простий echo"""
    await update.message.reply_text(f"🔔 Ви написали: {update.message.text}")

async def main():
    """Головна функція"""
    try:
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        
        # Додаємо обробники
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Встановлюємо вебхук
        await application.initialize()
        await application.bot.set_webhook(WEBHOOK_URL)
        await application.start()
        
        logger.info("✅ Екстрений бот запущено!")
        logger.info(f"🌐 Вебхук: {WEBHOOK_URL}")
        
        # Чекаємо
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Запуск екстреного бота...")
    asyncio.run(main())