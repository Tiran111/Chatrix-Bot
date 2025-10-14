from telegram import ReplyKeyboardMarkup

def get_search_navigation():
    """Клавіатура для навігації при пошуку"""
    keyboard = [
        ['❤️ Лайк', '➡️ Далі'],
        ['🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_gallery_menu():
    """Меню галереї"""
    keyboard = [
        ['📷 Додати фото', '👀 Переглянути галерею'],
        ['🔙 Головне меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_gallery_navigation():
    """Навігація по галереї"""
    keyboard = [
        ['⬅️ Попереднє', '➡️ Наступне'],
        ['📝 Профіль', '🔙 Галерея']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_profile_navigation():
    """Навігація профілю"""
    keyboard = [
        ['✏️ Редагувати профіль', '📷 Моя галерея'],
        ['🔙 Головне меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_users_keyboard():
    """Клавіатура для адмін-управління користувачами"""
    keyboard = [
        ['📋 Список користувачів', '🔍 Пошук користувача'],
        ['🚫 Заблокувати', '✅ Розблокувати'],
        ['📋 Список заблокованих', '🔙 Назад до адмін-панелі']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_ban_keyboard():
    """Клавіатура для адмін-блокування"""
    keyboard = [
        ['🚫 Заблокувати користувача', '✅ Розблокувати користувача'],
        ['📋 Список заблокованих', '🔙 Назад до адмін-панелі']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_main_keyboard():
    """Головна клавіатура адміна"""
    keyboard = [
        ['📊 Статистика', '👥 Користувачі'],
        ['📢 Розсилка', '🔄 Оновити базу'],
        ['🚫 Блокування', '📈 Детальна статистика'],
        ['🔙 Головне меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_contact_admin_keyboard():
    """Клавіатура для зв'язку з адміном"""
    keyboard = [
        ['🔙 Скасувати']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """Універсальна клавіатура скасування"""
    keyboard = [
        ['🔙 Скасувати']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_photo_upload_keyboard():
    """Клавіатура для завантаження фото"""
    keyboard = [
        ['🔙 Завершити']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_top_selection_keyboard():
    """Клавіатура для вибору топу"""
    keyboard = [
        ['👨 Топ чоловіків', '👩 Топ жінок'],
        ['🏆 Загальний топ', '🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_gender_selection_keyboard():
    """Клавіатура для вибору статі"""
    keyboard = [
        ['👨', '👩'],
        ['🔙 Скасувати']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_seeking_gender_keyboard():
    """Клавіатура для вибору кого шукає"""
    keyboard = [
        ['👩 Дівчину', '👨 Хлопця'],
        ['👫 Всіх'],
        ['🔙 Скасувати']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_goal_selection_keyboard():
    """Клавіатура для вибору цілі знайомства"""
    keyboard = [
        ['💞 Серйозні стосунки', '👥 Дружба'],
        ['🎉 Разові зустрічі', '🏃 Активний відпочинок'],
        ['🔙 Скасувати']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_city_search_keyboard():
    """Клавіатура для пошуку за містом"""
    keyboard = [
        ['🏙️ Київ', '🏙️ Львів'],
        ['🏙️ Одеса', '🏙️ Харків'],
        ['🏙️ Дніпро', '🏙️ Запоріжжя'],
        ['🔙 Меню']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_match_actions_keyboard():
    """Клавіатура дій для матчів"""
    keyboard = [
        ['💌 Написати повідомлення', '👤 Переглянути профіль'],
        ['🔙 Мої матчі']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_like_actions_keyboard():
    """Клавіатура дій для лайків"""
    keyboard = [
        ['❤️ Взаємний лайк', '👤 Переглянути профіль'],
        ['🔙 Назад до лайків']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_edit_profile_keyboard():
    """Клавіатура для редагування профілю"""
    keyboard = [
        ['✏️ Змінити вік', '✏️ Змінити стать'],
        ['✏️ Змінити місто', '✏️ Змінити ціль'],
        ['✏️ Змінити опис', '📷 Змінити фото'],
        ['🔙 Мій профіль']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_broadcast_confirmation_keyboard():
    """Клавіатура підтвердження розсилки"""
    keyboard = [
        ['✅ Так, надіслати', '❌ Ні, скасувати'],
        ['🔙 Адмін панель']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)