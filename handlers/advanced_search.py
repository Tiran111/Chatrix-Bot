from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
from utils.states import user_states, States
import logging

logger = logging.getLogger(__name__)

async def start_advanced_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок розширеного пошуку"""
    user = update.effective_user
    
    # Очищаємо попередні дані пошуку
    context.user_data.pop('advanced_search', None)
    
    # Встановлюємо стан
    user_states[user.id] = States.ADVANCED_SEARCH_GENDER
    
    # Клавіатура для вибору статі
    keyboard = [
        [KeyboardButton("👩 Дівчата"), KeyboardButton("👨 Хлопці")],
        [KeyboardButton("👫 Всі"), KeyboardButton("🔙 Головне меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔍 *Розширений пошук*\n\n"
        "Оберіть стать для пошуку:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_advanced_search_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору статі для розширеного пошуку"""
    user = update.effective_user
    text = update.message.text
    
    # Перевіряємо стан
    if user_states.get(user.id) != States.ADVANCED_SEARCH_GENDER:
        await update.message.reply_text(
            "❌ Будь ласка, почніть пошук спочатку",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    # Зберігаємо вибір статі
    if not context.user_data.get('advanced_search'):
        context.user_data['advanced_search'] = {}
    
    if text == "👩 Дівчата":
        context.user_data['advanced_search']['gender'] = 'female'
        gender_display = "👩 Дівчата"
    elif text == "👨 Хлопці":
        context.user_data['advanced_search']['gender'] = 'male' 
        gender_display = "👨 Хлопці"
    else:  # 👫 Всі
        context.user_data['advanced_search']['gender'] = 'all'
        gender_display = "👫 Всі"
    
    # Оновлюємо стан
    user_states[user.id] = States.ADVANCED_SEARCH_CITY
    
    # Клавіатура для вибору міста
    keyboard = [
        [KeyboardButton("🏙️ Київ"), KeyboardButton("🏙️ Харків")],
        [KeyboardButton("🏙️ Одеса"), KeyboardButton("🏙️ Дніпро")],
        [KeyboardButton("🏙️ Львів"), KeyboardButton("🏙️ Запоріжжя")],
        [KeyboardButton("🏙️ Вінниця"), KeyboardButton("🏙️ Житомир")],
        [KeyboardButton("🏙️ Івано-Франківськ"), KeyboardButton("🏙️ Кропивницький")],
        [KeyboardButton("🏙️ Луцьк"), KeyboardButton("🏙️ Миколаїв")],
        [KeyboardButton("🏙️ Полтава"), KeyboardButton("🏙️ Рівне")],
        [KeyboardButton("🏙️ Суми"), KeyboardButton("🏙️ Тернопіль")],
        [KeyboardButton("🏙️ Ужгород"), KeyboardButton("🏙️ Херсон")],
        [KeyboardButton("🏙️ Хмельницький"), KeyboardButton("🏙️ Черкаси")],
        [KeyboardButton("🏙️ Чернівці"), KeyboardButton("🏙️ Чернігів")],
        [KeyboardButton("✏️ Ввести інше місто"), KeyboardButton("🔙 Головне меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ Стать: {gender_display}\n\n"
        "🏙️ Тепер оберіть місто для пошуку:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_advanced_search_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору міста для розширеного пошуку"""
    user = update.effective_user
    text = update.message.text
    
    # Перевіряємо стан
    if user_states.get(user.id) != States.ADVANCED_SEARCH_CITY:
        await update.message.reply_text(
            "❌ Будь ласка, почніть пошук спочатку",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    if text == "✏️ Ввести інше місто":
        user_states[user.id] = States.ADVANCED_SEARCH_CITY_INPUT
        await update.message.reply_text(
            "🏙️ Введіть назву міста:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Скасувати")]], resize_keyboard=True)
        )
        return
    
    # Видаляємо емодзі з назви міста
    city = text.replace('🏙️ ', '').strip()
    
    # Зберігаємо місто
    context.user_data['advanced_search']['city'] = city
    
    # Оновлюємо стан
    user_states[user.id] = States.ADVANCED_SEARCH_GOAL
    
    # Клавіатура для вибору цілі
    keyboard = [
        [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
        [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
        [KeyboardButton("🔙 Головне меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ Стать: {get_gender_display(context.user_data['advanced_search']['gender'])}\n"
        f"✅ Місто: {city}\n\n"
        "🎯 Тепер оберіть ціль знайомства:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_advanced_search_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка введення міста вручну"""
    user = update.effective_user
    text = update.message.text
    
    if user_states.get(user.id) != States.ADVANCED_SEARCH_CITY_INPUT:
        return
    
    if text == "🔙 Скасувати":
        await start_advanced_search(update, context)
        return
    
    # Зберігаємо місто
    context.user_data['advanced_search']['city'] = text
    
    # Оновлюємо стан
    user_states[user.id] = States.ADVANCED_SEARCH_GOAL
    
    # Клавіатура для вибору цілі
    keyboard = [
        [KeyboardButton("💞 Серйозні стосунки"), KeyboardButton("👥 Дружба")],
        [KeyboardButton("🎉 Разові зустрічі"), KeyboardButton("🏃 Активний відпочинок")],
        [KeyboardButton("🔙 Головне меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"✅ Стать: {get_gender_display(context.user_data['advanced_search']['gender'])}\n"
        f"✅ Місто: {text}\n\n"
        "🎯 Тепер оберіть ціль знайомства:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_advanced_search_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору цілі та виконання пошуку"""
    user = update.effective_user
    text = update.message.text
    
    # Перевіряємо стан
    if user_states.get(user.id) != States.ADVANCED_SEARCH_GOAL:
        await update.message.reply_text(
            "❌ Будь ласка, почніть пошук спочатку",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    # Визначаємо ціль
    goal_map = {
        '💞 Серйозні стосунки': 'Серйозні стосунки',
        '👥 Дружба': 'Дружба',
        '🎉 Разові зустрічі': 'Разові зустрічі', 
        '🏃 Активний відпочинок': 'Активний відпочинок'
    }
    
    goal = goal_map.get(text)
    if not goal:
        await update.message.reply_text(
            "❌ Будь ласка, оберіть ціль зі списку",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    # Зберігаємо ціль
    context.user_data['advanced_search']['goal'] = goal
    
    # Виконуємо пошук
    await execute_advanced_search(update, context)

async def execute_advanced_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Виконання розширеного пошуку за всіма критеріями"""
    user = update.effective_user
    search_data = context.user_data.get('advanced_search', {})
    
    if not search_data:
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    # Отримуємо параметри пошуку
    gender = search_data.get('gender', 'all')
    city = search_data.get('city', '')
    goal = search_data.get('goal', '')
    
    # Виконуємо пошук в базі даних
    users = db.search_users_advanced(
        user_id=user.id,
        gender=gender,
        city=city,
        goal=goal
    )
    
    # Зберігаємо результати
    context.user_data['search_users'] = users
    context.user_data['current_index'] = 0
    context.user_data['search_type'] = 'advanced'
    
    # Скидаємо стан
    user_states[user.id] = States.START
    
    if users:
        # Показуємо перший результат
        from handlers.search import show_user_profile
        user_data = users[0]
        
        search_info = (
            f"🔍 *Результати розширеного пошуку:*\n"
            f"• Стать: {get_gender_display(gender)}\n"
            f"• Місто: {city}\n" 
            f"• Ціль: {goal}\n"
            f"• Знайдено: {len(users)} анкет\n"
        )
        
        await show_user_profile(update, context, user_data, search_info)
    else:
        await update.message.reply_text(
            f"😔 Не знайдено анкет за вашими критеріями:\n"
            f"• Стать: {get_gender_display(gender)}\n"
            f"• Місто: {city}\n"
            f"• Ціль: {goal}",
            reply_markup=get_main_menu(user.id),
            parse_mode='Markdown'
        )

def get_gender_display(gender):
    """Повертає відображення статі"""
    if gender == 'female':
        return "👩 Дівчата"
    elif gender == 'male':
        return "👨 Хлопці"
    else:
        return "👫 Всі"