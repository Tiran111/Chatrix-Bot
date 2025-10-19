import os
import logging
from flask import Flask, request, jsonify
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
import requests

# Імпорт власних модулів
from config import initialize_config, TOKEN, ADMIN_ID, DATABASE_URL, RENDER, WEBHOOK_URL, KEEP_ALIVE_INTERVAL
from database import db
from states import States, user_states, user_profiles, gallery_view_data

# Ініціалізація конфігурації
initialize_config()

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація Flask додатку
app = Flask(__name__)

# Ініціалізація бота
bot = telebot.TeleBot(TOKEN)

# ========== КЛАВІАТУРИ ==========

def get_main_menu_keyboard():
    """Головне меню"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("👤 Мій профіль"),
        KeyboardButton("🔍 Пошук анкет"),
        KeyboardButton("⭐ Преміум"),
        KeyboardButton("📞 Контакти"),
        KeyboardButton("ℹ️ Допомога")
    )
    return keyboard

def get_profile_keyboard():
    """Меню профілю"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("✏️ Редагувати профіль"),
        KeyboardButton("📷 Мої фото"),
        KeyboardButton("⬅️ Назад")
    )
    return keyboard

def get_edit_profile_keyboard():
    """Меню редагування профілю"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("✏️ Змінити вік"),
        KeyboardButton("✏️ Змінити стать"),
        KeyboardButton("✏️ Змінити місто"),
        KeyboardButton("✏️ Змінити ціль"),
        KeyboardButton("✏️ Змінити біо"),
        KeyboardButton("📷 Додати фото"),
        KeyboardButton("⬅️ Назад до профілю")
    )
    return keyboard

def get_gender_keyboard():
    """Вибір статі"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("👨 Чоловік"),
        KeyboardButton("👩 Жінка"),
        KeyboardButton("⬅️ Назад")
    )
    return keyboard

def get_seeking_gender_keyboard():
    """Вибір статі для пошуку"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("👨 Чоловіків"),
        KeyboardButton("👩 Жінок"),
        KeyboardButton("👥 Всіх"),
        KeyboardButton("⬅️ Назад")
    )
    return keyboard

def get_goal_keyboard():
    """Вибір цілей"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("💕 Серйозні стосунки"),
        KeyboardButton("💬 Спілкування"),
        KeyboardButton("🍷 Дружба"),
        KeyboardButton("🏃‍♂️ Прогулянки"),
        KeyboardButton("⬅️ Назад")
    )
    return keyboard

def get_gallery_keyboard():
    """Меню галереї"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("➕ Додати фото"),
        KeyboardButton("🗑️ Видалити фото"),
        KeyboardButton("⭐ Зробити головним"),
        KeyboardButton("⬅️ Назад")
    )
    return keyboard

def get_back_keyboard():
    """Проста кнопка назад"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("⬅️ Назад"))
    return keyboard

def get_admin_keyboard():
    """Адмін меню"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 Статистика"),
        KeyboardButton("🔍 Пошук користувача"),
        KeyboardButton("🚫 Заблокувати"),
        KeyboardButton("✅ Розблокувати"),
        KeyboardButton("📢 Розсилка"),
        KeyboardButton("⬅️ Головне меню")
    )
    return keyboard

# ========== ОСНОВНІ ФУНКЦІЇ ==========

def set_user_state(user_id, state):
    """Встановлення стану користувача"""
    user_states[user_id] = state

def get_user_state(user_id):
    """Отримання стану користувача"""
    return user_states.get(user_id, States.START)

def save_user_profile(user_id, profile_data):
    """Збереження профілю користувача"""
    if user_id not in user_profiles:
        user_profiles[user_id] = {}
    user_profiles[user_id].update(profile_data)

def get_user_profile(user_id):
    """Отримання профілю користувача"""
    return user_profiles.get(user_id, {})

def is_user_banned(user_id):
    """Перевірка чи заблокований користувач"""
    user = db.get_user(user_id)
    return user and user['is_banned']

# ========== ОБРОБНИКИ КОМАНД ==========

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'OK'

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обробка команди /start"""
    user_id = message.from_user.id
    
    # Додаємо користувача в базу
    db.add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Перевірка на бан
    if is_user_banned(user_id):
        bot.send_message(user_id, "❌ Ви заблоковані в системі.")
        return
    
    # Скидаємо стан
    set_user_state(user_id, States.START)
    
    # Вітальне повідомлення
    welcome_text = """
    👋 Вітаю в Dating Bot!
    
    Тут ти можеш знайти нові знайомства, спілкування та можливо кохання!
    
    🎯 Заповни профіль та почни пошук!
    """
    
    bot.send_message(user_id, welcome_text, reply_markup=get_main_menu_keyboard())

@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == States.START)
def handle_main_menu(message):
    """Обробка головного меню"""
    user_id = message.from_user.id
    text = message.text
    
    if text == "👤 Мій профіль":
        show_profile(message)
    elif text == "🔍 Пошук анкет":
        start_search(message)
    elif text == "⭐ Преміум":
        show_premium(message)
    elif text == "📞 Контакти":
        show_contacts(message)
    elif text == "ℹ️ Допомога":
        show_help(message)
    elif str(user_id) == str(ADMIN_ID) and text == "👑 Адмін панель":
        show_admin_panel(message)
    else:
        bot.send_message(user_id, "Оберіть опцію з меню:", reply_markup=get_main_menu_keyboard())

# ========== ПРОФІЛЬ ==========

def show_profile(message):
    """Показати профіль користувача"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "❌ Профіль не знайдено.")
        return
    
    profile_text = f"""
👤 *Ваш профіль:*

*Ім'я:* {user['first_name']} {user['last_name'] or ''}
*Вік:* {user['age'] or 'Не вказано'}
*Стать:* {user['gender'] or 'Не вказано'}
*Місто:* {user['city'] or 'Не вказано'}
*Шукаю:* {user['seeking_gender'] or 'Не вказано'}
*Ціль:* {user['goal'] or 'Не вказано'}
*Біо:* {user['bio'] or 'Не вказано'}
    """
    
    # Відправляємо головне фото якщо є
    main_photo = db.get_main_photo(user_id)
    if main_photo:
        try:
            bot.send_photo(user_id, main_photo['file_id'], caption=profile_text, 
                         parse_mode='Markdown', reply_markup=get_profile_keyboard())
            return
        except Exception as e:
            logger.error(f"Помилка відправки фото: {e}")
    
    # Якщо фото немає або помилка
    bot.send_message(user_id, profile_text, parse_mode='Markdown', 
                   reply_markup=get_profile_keyboard())

@bot.message_handler(func=lambda message: message.text == "✏️ Редагувати профіль")
def handle_edit_profile(message):
    """Редагування профілю"""
    user_id = message.from_user.id
    bot.send_message(user_id, "Оберіть що хочете змінити:", 
                   reply_markup=get_edit_profile_keyboard())

@bot.message_handler(func=lambda message: message.text == "📷 Мої фото")
def handle_my_photos(message):
    """Показати мої фото"""
    user_id = message.from_user.id
    photos = db.get_user_photos(user_id)
    
    if not photos:
        bot.send_message(user_id, "📷 У вас ще немає фотографій.", 
                       reply_markup=get_gallery_keyboard())
        return
    
    for photo in photos:
        try:
            caption = "⭐ Головне фото" if photo['is_main'] else f"Фото #{photo['id']}"
            bot.send_photo(user_id, photo['file_id'], caption=caption)
        except Exception as e:
            logger.error(f"Помилка відправки фото: {e}")
    
    bot.send_message(user_id, f"📸 Усього фотографій: {len(photos)}", 
                   reply_markup=get_gallery_keyboard())

# ========== ПОШУК ==========

def start_search(message):
    """Початок пошуку"""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user or not user['age'] or not user['gender']:
        bot.send_message(user_id, "❌ Заповніть спочатку свій профіль!")
        return
    
    # Простий пошук - знаходимо першого підходящого користувача
    search_results = db.search_users(
        current_user_id=user_id,
        gender=user['seeking_gender'] if user['seeking_gender'] != '👥 Всіх' else None
    )
    
    if not search_results:
        bot.send_message(user_id, "😔 Наразі немає підходящих анкет. Спробуйте пізніше.")
        return
    
    # Показуємо першу анкету
    show_user_profile(message, search_results[0]['user_id'])

def show_user_profile(message, profile_user_id, index=0):
    """Показати анкету користувача"""
    user_id = message.from_user.id
    profile_user = db.get_user(profile_user_id)
    
    if not profile_user:
        bot.send_message(user_id, "❌ Анкету не знайдено.")
        return
    
    profile_text = f"""
👤 *Анкета:*

*Ім'я:* {profile_user['first_name']} {profile_user['last_name'] or ''}
*Вік:* {profile_user['age'] or 'Не вказано'}
*Стать:* {profile_user['gender'] or 'Не вказано'}
*Місто:* {profile_user['city'] or 'Не вказано'}
*Ціль:* {profile_user['goal'] or 'Не вказано'}
*Біо:* {profile_user['bio'] or 'Не вказано'}
    """
    
    # Відправляємо головне фото
    main_photo = db.get_main_photo(profile_user_id)
    if main_photo:
        try:
            # Створюємо inline клавіатуру для дій
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{profile_user_id}"),
                InlineKeyboardButton("➡️ Далі", callback_data="next_profile"),
                InlineKeyboardButton("📸 Галерея", callback_data=f"gallery_{profile_user_id}")
            )
            
            bot.send_photo(user_id, main_photo['file_id'], caption=profile_text,
                         parse_mode='Markdown', reply_markup=keyboard)
            return
        except Exception as e:
            logger.error(f"Помилка відправки фото: {e}")
    
    # Якщо фото немає
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{profile_user_id}"),
        InlineKeyboardButton("➡️ Далі", callback_data="next_profile")
    )
    
    bot.send_message(user_id, profile_text, parse_mode='Markdown', reply_markup=keyboard)

# ========== CALLBACK HANDLERS ==========

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обробка callback кнопок"""
    user_id = call.from_user.id
    
    if call.data.startswith('like_'):
        profile_user_id = int(call.data.split('_')[1])
        db.add_like(user_id, profile_user_id)
        bot.answer_callback_query(call.id, "❤️ Ви поставили лайк!")
        
    elif call.data == 'next_profile':
        # Знаходимо наступну анкету
        user = db.get_user(user_id)
        search_results = db.search_users(
            current_user_id=user_id,
            gender=user['seeking_gender'] if user['seeking_gender'] != '👥 Всіх' else None
        )
        
        if search_results:
            show_user_profile(call.message, search_results[0]['user_id'])
        else:
            bot.send_message(user_id, "😔 Більше анкет немає.")
        
    elif call.data.startswith('gallery_'):
        profile_user_id = int(call.data.split('_')[1])
        show_user_gallery(call.message, profile_user_id)

def show_user_gallery(message, profile_user_id):
    """Показати галерею користувача"""
    user_id = message.from_user.id
    photos = db.get_user_photos(profile_user_id)
    
    if not photos:
        bot.send_message(user_id, "📷 У цього користувача ще немає фотографій.")
        return
    
    for photo in photos:
        try:
            caption = "⭐ Головне фото" if photo['is_main'] else f"Фото #{photo['id']}"
            bot.send_photo(user_id, photo['file_id'], caption=caption)
        except Exception as e:
            logger.error(f"Помилка відправки фото: {e}")

# ========== ДОДАТКОВІ ФУНКЦІЇ ==========

def show_premium(message):
    """Преміум функції"""
    user_id = message.from_user.id
    premium_text = """
    ⭐ *Преміум функції:*
    
    🚀 *Розширений пошук* - більше фільтрів
    👀 *Невидимка* - перегляд без слідів
    💌 *Необмежені повідомлення*
    📊 *Статистика профілю*
    
    💰 *Вартість:* 99 грн/місяць
    
    Для активації звертайтесь до адміністратора: @admin
    """
    bot.send_message(user_id, premium_text, parse_mode='Markdown')

def show_contacts(message):
    """Контактна інформація"""
    user_id = message.from_user.id
    contacts_text = """
    📞 *Контакти:*
    
    👨‍💼 *Адміністратор:* @admin
    📧 *Email:* admin@example.com
    🌐 *Сайт:* example.com
    
    ⚠️ *Правила:*
    - Поважайте інших користувачів
    - Не розголошуйте особисту інформацію
    - Не спамте
    
    За порушення - бан!
    """
    bot.send_message(user_id, contacts_text, parse_mode='Markdown')

def show_help(message):
    """Довідка"""
    user_id = message.from_user.id
    help_text = """
    ℹ️ *Довідка:*
    
    *Як користуватись ботом:*
    1. Заповніть профіль (/start)
    2. Додайте фото
    3. Почніть пошук анкет
    4. Спілкуйтесь та знаходьте нових друзів!
    
    *Основні команди:*
    /start - Головне меню
    /profile - Мій профіль
    /search - Пошук анкет
    
    *Проблеми?* Звертайтесь до адміністратора: @admin
    """
    bot.send_message(user_id, help_text, parse_mode='Markdown')

def show_admin_panel(message):
    """Адмін панель"""
    user_id = message.from_user.id
    if str(user_id) != str(ADMIN_ID):
        bot.send_message(user_id, "❌ Доступ заборонено!")
        return
    
    users_count = len(db.get_all_users())
    admin_text = f"""
    👑 *Адмін панель*
    
    📊 *Користувачів:* {users_count}
    ⚠️ *Заблоковано:* {len([u for u in db.get_all_users() if u['is_banned']])}
    
    Оберіть дію:
    """
    bot.send_message(user_id, admin_text, parse_mode='Markdown', 
                   reply_markup=get_admin_keyboard())

# ========== KEEP-ALIVE FUNCTION ==========

def keep_alive():
    """Функція для підтримки активності на Render"""
    while True:
        try:
            # Просто чекаємо
            time.sleep(KEEP_ALIVE_INTERVAL)
            logger.info("🔄 Keep-alive: бот активний")
        except Exception as e:
            logger.error(f"❌ Помилка в keep-alive: {e}")

# ========== ЗАПУСК БОТА ==========

def setup_bot():
    """Налаштування бота"""
    try:
        if RENDER:
            # На Render використовуємо webhook
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=WEBHOOK_URL)
            logger.info(f"✅ Webhook встановлено: {WEBHOOK_URL}")
        else:
            # Локально використовуємо polling
            bot.remove_webhook()
            logger.info("✅ Webhook видалено, використовується polling")
        
        # Запускаємо keep-alive в окремому потоці
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        logger.info("✅ Keep-alive thread запущено")
        
    except Exception as e:
        logger.error(f"❌ Помилка налаштування бота: {e}")

@app.route('/')
def home():
    """Головна сторінка"""
    return "🤖 Dating Bot is running!"

@app.route('/health')
def health_check():
    """Перевірка здоров'я"""
    return jsonify({"status": "healthy", "bot": "running"})

if __name__ == '__main__':
    logger.info("🚀 Запуск Dating Bot...")
    setup_bot()
    
    if RENDER:
        # На Render запускаємо Flask сервер
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Локально запускаємо polling
        logger.info("🔄 Запуск polling...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)