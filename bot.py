# bot.py - Простий бот тільки з полінгом
import logging
import asyncio
import signal
import sys
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, 
    filters, ConversationHandler
)

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Імпорт модулів
try:
    from database_postgres import db
    logger.info("✅ Використовується PostgreSQL база даних")
except ImportError as e:
    logger.error(f"❌ Помилка імпорту бази даних: {e}")
    raise

try:
    from config import ADMIN_ID, TOKEN
except ImportError as e:
    logger.error(f"❌ Помилка імпорту конфігурації: {e}")
    raise

# Стани для ConversationHandler
PROFILE_AGE, PROFILE_GENDER, PROFILE_CITY, PROFILE_SEEKING_GENDER, PROFILE_GOAL, PROFILE_BIO = range(6)

# Глобальна змінна для бота
application = None

# ==================== ФУНКЦІЇ ПРОФІЛЮ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    # Додаємо користувача в базу
    success = db.add_user(user.id, user.username, user.first_name)
    
    if success:
        await update.message.reply_text(
            f"👋 Вітаю, {user.first_name}!\n\n"
            "🤖 Я - Chatrix Bot, створений для знайомств та спілкування.\n\n"
            "📝 Давайте створимо ваш профіль, щоб інші користувачі могли вас знайти!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Перевіряємо чи є профіль
        user_data, is_complete = db.get_user_profile(user.id)
        
        if is_complete:
            await show_profile(update, context)
        else:
            await start_profile_creation(update, context)
    else:
        await update.message.reply_text("❌ Помилка реєстрації. Спробуйте пізніше.")

async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок створення профілю"""
    await update.message.reply_text(
        "📝 Давайте створимо ваш профіль!\n\n"
        "Скільки вам років? (Введіть число від 18 до 100)",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROFILE_AGE

async def profile_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка віку"""
    try:
        age = int(update.message.text)
        if age < 18 or age > 100:
            await update.message.reply_text("⚠️ Будь ласка, введіть вік від 18 до 100 років:")
            return PROFILE_AGE
        
        context.user_data['age'] = age
        
        # Клавіатура для вибору статі
        keyboard = [
            ["👨 Чоловік", "👩 Жінка"],
            ["🚫 Скасувати"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🎯 Ваша стать?",
            reply_markup=reply_markup
        )
        return PROFILE_GENDER
        
    except ValueError:
        await update.message.reply_text("⚠️ Будь ласка, введіть коректний вік (число):")
        return PROFILE_AGE

async def profile_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка статі"""
    text = update.message.text
    
    if "👨" in text:
        context.user_data['gender'] = 'male'
    elif "👩" in text:
        context.user_data['gender'] = 'female'
    elif "🚫" in text:
        await update.message.reply_text("❌ Створення профілю скасовано.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        await update.message.reply_text("⚠️ Будь ласка, оберіть стать з клавіатури:")
        return PROFILE_GENDER
    
    await update.message.reply_text(
        "🏙️ В якому місті ви живете? (Наприклад: Київ, Львів, Одеса)",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROFILE_CITY

async def profile_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка міста"""
    city = update.message.text.strip()
    
    if len(city) < 2:
        await update.message.reply_text("⚠️ Будь ласка, введіть коректну назву міста:")
        return PROFILE_CITY
    
    context.user_data['city'] = city
    
    # Клавіатура для вибору кого шукає
    keyboard = [
        ["👨 Чоловіків", "👩 Жінок", "👫 Всіх"],
        ["🚫 Скасувати"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔍 Кого ви хочете знайти?",
        reply_markup=reply_markup
    )
    return PROFILE_SEEKING_GENDER

async def profile_seeking_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка пошуку статі"""
    text = update.message.text
    
    if "👨" in text:
        context.user_data['seeking_gender'] = 'male'
    elif "👩" in text:
        context.user_data['seeking_gender'] = 'female'
    elif "👫" in text:
        context.user_data['seeking_gender'] = 'all'
    elif "🚫" in text:
        await update.message.reply_text("❌ Створення профілю скасовано.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        await update.message.reply_text("⚠️ Будь ласка, оберіть з клавіатури:")
        return PROFILE_SEEKING_GENDER
    
    # Клавіатура для вибору цілі
    keyboard = [
        ["💕 Серйозні стосунки", "👥 Дружба", "💬 Спілкування"],
        ["🎭 Флірт", "🚫 Скасувати"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎯 Яка ваша ціль?",
        reply_markup=reply_markup
    )
    return PROFILE_GOAL

async def profile_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка цілі"""
    text = update.message.text
    
    goal_map = {
        "💕 Серйозні стосунки": "Серйозні стосунки",
        "👥 Дружба": "Дружба", 
        "💬 Спілкування": "Спілкування",
        "🎭 Флірт": "Флірт"
    }
    
    if text in goal_map:
        context.user_data['goal'] = goal_map[text]
    elif "🚫" in text:
        await update.message.reply_text("❌ Створення профілю скасовано.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        await update.message.reply_text("⚠️ Будь ласка, оберіть з клавіатури:")
        return PROFILE_GOAL
    
    await update.message.reply_text(
        "📖 Розкажіть трохи про себе:\n"
        "(Ваші інтереси, хобі, що шукаєте тощо)\n\n"
        "💡 Наприклад: 'Люблю подорожі, кіно та активний відпочинок. Шукаю цікавих співрозмовників.'",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROFILE_BIO

async def profile_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка біо"""
    bio = update.message.text.strip()
    
    if len(bio) < 10:
        await update.message.reply_text("⚠️ Будь ласка, напишіть трошки більше про себе (мінімум 10 символів):")
        return PROFILE_BIO
    
    context.user_data['bio'] = bio
    
    # Зберігаємо профіль в базу
    user = update.effective_user
    success = db.update_or_create_user_profile(
        telegram_id=user.id,
        age=context.user_data['age'],
        gender=context.user_data['gender'],
        city=context.user_data['city'],
        seeking_gender=context.user_data['seeking_gender'],
        goal=context.user_data['goal'],
        bio=context.user_data['bio']
    )
    
    if success:
        await update.message.reply_text(
            "🎉 Ваш профіль успішно створено!\n\n"
            "Тепер ви можете:\n"
            "• 📱 Переглядати анкети\n"  
            "• ❤️ Ставити лайки\n"
            "• 💌 Спілкуватися з матчами\n"
            "• ⚙️ Редагувати профіль",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_profile(update, context)
    else:
        await update.message.reply_text("❌ Помилка збереження профілю. Спробуйте пізніше.")
    
    return ConversationHandler.END

async def cancel_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скасування створення профілю"""
    await update.message.reply_text(
        "❌ Створення профілю скасовано.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати профіль користувача"""
    user = update.effective_user
    user_data, is_complete = db.get_user_profile(user.id)
    
    if not user_data or not is_complete:
        await update.message.reply_text(
            "📝 Ваш профіль ще не заповнений. Давайте створимо його!",
            reply_markup=ReplyKeyboardRemove()
        )
        await start_profile_creation(update, context)
        return
    
    # Формуємо текст профілю
    profile_text = (
        f"👤 <b>Ваш профіль</b>\n\n"
        f"🆔 ID: {user_data['telegram_id']}\n"
        f"👤 Ім'я: {user_data['first_name']}\n"
        f"📅 Вік: {user_data['age']}\n"
        f"🎯 Стать: {'👨 Чоловік' if user_data['gender'] == 'male' else '👩 Жінка'}\n"
        f"🏙️ Місто: {user_data['city']}\n"
        f"🔍 Шукаю: {get_seeking_text(user_data['seeking_gender'])}\n"
        f"🎯 Ціль: {user_data['goal']}\n"
        f"📖 Про себе: {user_data['bio']}\n\n"
        f"⭐ Рейтинг: {user_data['rating']}/10\n"
        f"❤️ Лайків: {user_data['likes_count']}\n"
    )
    
    # Перевіряємо фото
    photos = db.get_profile_photos(user.id)
    if photos:
        # Відправляємо фото з описом
        await update.message.reply_photo(
            photo=photos[0],
            caption=profile_text,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            profile_text,
            parse_mode='HTML'
        )

def get_seeking_text(seeking_gender):
    """Отримати текст для пошуку"""
    if seeking_gender == 'male':
        return '👨 Чоловіків'
    elif seeking_gender == 'female':
        return '👩 Жінок'
    else:
        return '👫 Всіх'

# ==================== ОСНОВНІ КОМАНДИ ====================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = (
        "🤖 <b>Chatrix Bot - Довідка</b>\n\n"
        "📋 <b>Основні команди:</b>\n"
        "/start - Початок роботи та створення профілю\n"
        "/profile - Перегляд та редагування профілю\n"
        "/search - Пошук анкет\n"
        "/likes - Перегляд лайків\n"
        "/matches - Ваші матчі\n"
        "/stats - Статистика\n"
        "/help - Ця довідка\n\n"
        "💡 <b>Як користуватися:</b>\n"
        "1. Створіть профіль (/start)\n"
        "2. Переглядайте анкети (/search)\n"
        "3. Ставте лайки ❤️\n"
        "4. Спілкуйтеся з матчами 💌\n\n"
        "⚙️ Для адміністраторів: /admin"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /profile"""
    await show_profile(update, context)

# ==================== ОБРОБНИКИ ПОМИЛОК ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"❌ Помилка в боті: {context.error}", exc_info=True)

# ==================== НАЛАШТУВАННЯ ОБРОБНИКІВ ====================

def setup_handlers(app):
    """Налаштування обробників"""
    
    # ConversationHandler для створення профілю
    profile_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_profile_creation)],
        states={
            PROFILE_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_age)],
            PROFILE_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_gender)],
            PROFILE_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_city)],
            PROFILE_SEEKING_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_seeking_gender)],
            PROFILE_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_goal)],
            PROFILE_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_bio)],
        },
        fallbacks=[CommandHandler('cancel', cancel_profile)]
    )
    
    # Основні команди
    app.add_handler(profile_conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    
    # Обробник помилок
    app.add_error_handler(error_handler)

# ==================== УПРАВЛІННЯ EVENT LOOP ====================

async def shutdown(signal, loop):
    """Коректне завершення роботи"""
    logger.info(f"🔄 Отримано сигнал {signal.name}...")
    global application
    
    if application:
        logger.info("🔄 Зупинка бота...")
        await application.stop()
        await application.shutdown()
        logger.info("✅ Бот зупинено")
    
    logger.info("🔄 Зупинка event loop...")
    loop.stop()

# ==================== ЗАПУСК БОТА ====================

async def main():
    """Запуск бота"""
    global application
    
    logger.info("🚀 Запуск Chatrix Bot...")
    
    # Перевірка токена
    import requests
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=10)
        if response.json().get('ok'):
            bot_info = response.json()['result']
            logger.info(f"✅ Бот знайдений: {bot_info['first_name']}")
        else:
            logger.error("❌ Бот не знайдений. Перевірте токен.")
            return
    except Exception as e:
        logger.error(f"❌ Помилка перевірки бота: {e}")
        return
    
    # Створюємо додаток
    application = Application.builder().token(TOKEN).build()
    
    # Додаємо обробники
    setup_handlers(application)
    
    # Налаштовуємо обробку сигналів
    loop = asyncio.get_event_loop()
    signals = (signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop))
        )
    
    # Запускаємо полінг
    logger.info("✅ Бот запущено в режимі полінгу")
    await application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        # Використовуємо uvloop для кращої продуктивності (якщо встановлено)
        try:
            import uvloop
            uvloop.install()
            logger.info("✅ Використовується uvloop")
        except ImportError:
            logger.info("ℹ️ uvloop не встановлено, використовується стандартний asyncio")
        
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
        sys.exit(1)