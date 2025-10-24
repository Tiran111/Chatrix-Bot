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

TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = "https://chatrix-bot-4m1p.onrender.com/webhook"
PORT = int(os.environ.get('PORT', 10000))

async def start(update: Update, context):
    """Обробник /start"""
    user = update.effective_user
    logger.info(f"🎯 Отримано /start від {user.id}")
    
    await update.message.reply_text(
        f"👋 Вітаю, {user.first_name}!\n\n"
        f"💞 *Chatrix* — це бот для знайомств!\n\n"
        f"🆔 Ваш ID: `{user.id}`\n"
        f"✅ Бот працює стабільно!\n\n"
        f"🎯 *Почнімо знайомство!*",
        parse_mode='Markdown'
    )

async def setup_handlers(application):
    """Налаштування обробників"""
    # Основні команди
    application.add_handler(CommandHandler("start", start))
    
    # Спроба додати ваші обробники
    try:
        from handlers.profile import start_profile_creation, show_my_profile
        from handlers.search import search_profiles, search_by_city
        from handlers.admin import handle_admin_actions
        
        # Додаємо ваші обробники
        application.add_handler(MessageHandler(filters.Regex('^(📝 Заповнити профіль|📝 Редагувати)$'), start_profile_creation))
        application.add_handler(MessageHandler(filters.Regex('^👤 Мій профіль$'), show_my_profile))
        application.add_handler(MessageHandler(filters.Regex('^💕 Пошук анкет$'), search_profiles))
        application.add_handler(MessageHandler(filters.Regex('^🏙️ По місту$'), search_by_city))
        application.add_handler(MessageHandler(filters.Regex('^(👑 Адмін панель|📊 Статистика)$'), handle_admin_actions))
        
        logger.info("✅ Всі обробники завантажено")
    except ImportError as e:
        logger.warning(f"⚠️ Не вдалося завантажити деякі обробники: {e}")
        # Додаємо простий echo обробник
        async def echo(update: Update, context):
            await update.message.reply_text(f"🔔 Ви написали: {update.message.text}")
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        logger.info("✅ Додано простий echo обробник")

async def main():
    """Головна функція"""
    try:
        print("=" * 50)
        print("🚀 Запуск Chatrix Bot...")
        print("=" * 50)
        
        # Перевірка бази даних
        try:
            from database_postgres import db
            user_count = db.get_users_count()
            print(f"📊 Користувачів в базі: {user_count}")
            print("✅ База даних працює")
        except Exception as e:
            print(f"❌ Помилка бази даних: {e}")
        
        # Створюємо бота
        application = Application.builder().token(TOKEN).build()
        
        # Налаштовуємо обробники
        await setup_handlers(application)
        
        # Встановлюємо вебхук
        await application.initialize()
        await application.bot.set_webhook(WEBHOOK_URL)
        
        print("✅ Бот ініціалізовано")
        print(f"🌐 Вебхук встановлено: {WEBHOOK_URL}")
        print("🟢 Бот готовий до роботи!")
        
        # Запускаємо бота з вебхуком
        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            secret_token='webhook_secret'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка запуску бота: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())