from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
try:
    from database_postgres import db
except ImportError:
    from database.models import db
from utils.states import user_states, States
from keyboards.main_menu import get_main_menu
from config import ADMIN_ID
from utils.states import user_states, States
from keyboards.main_menu import get_main_menu
from config import ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    try:
        user = update.effective_user
        
        logger.info(f"🆕 Користувач: {user.first_name} (ID: {user.id}) викликав /start")
        
        # Перевіряємо чи існує користувач, якщо ні - створюємо
        existing_user = db.get_user(user.id)
        if not existing_user:
            db.add_user(user.id, user.username, user.first_name)
            logger.info(f"✅ Користувач {user.id} доданий в базу")
        else:
            logger.info(f"✅ Користувач {user.id} вже існує в базі")
        
        # ... решта коду без змін
    
    # Додаємо користувача в базу
    db.add_user(user.id, user.username, user.first_name)
    
    # Скидаємо стан
    user_states[user.id] = States.START
    
    # Вітання
    welcome_text = (
        f"👋 Вітаю, {user.first_name}!\n\n"
        f"💞 *Chatrix* — це бот для знайомств, де ти можеш:\n\n"
        f"• 📝 Створити свою анкету\n"
        f"• 💕 Знаходити цікавих людей\n"
        f"• ❤️ Ставити лайки та отримувати матчі\n"
        f"• 🏆 Переглядати топ користувачів\n"
        f"• 🏙️ Шукати за містом\n\n"
        f"🎯 *Почнімо знайомство!*"
    )
    
    # Перевіряємо чи заповнений профіль
    user_data, is_complete = db.get_user_profile(user.id)
    
    if not is_complete:
        welcome_text += "\n\n📝 *Для початку заповни свою анкету*"
        keyboard = [['📝 Заповнити профіль']]
    else:
        keyboard = [
            ['💕 Пошук анкет', '🏙️ По місту'],
            ['👤 Мій профіль', '❤️ Хто мене лайкнув'],
            ['💌 Мої матчі', '🏆 Топ'],
            ["👨‍💼 Зв'язок з адміном"]
        ]
    
    if user.id == ADMIN_ID:
        keyboard.append(['👑 Адмін панель'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    print(f"✅ Стартове повідомлення відправлено для {user.first_name}")
