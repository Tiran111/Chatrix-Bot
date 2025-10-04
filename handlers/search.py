from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu, get_search_navigation
from utils.states import user_states, States
from handlers.notifications import notification_system

# Допоміжна функція для форматування профілю - ОНОВЛЕНА ВЕРСІЯ З РЕЙТИНГОМ
def format_profile_text(user_data, title=""):
    """Форматування тексту профілю з рейтингом"""
    if isinstance(user_data, dict):
        # Якщо user_data - словник
        gender_display = "👨 Чоловік" if user_data.get('gender') == 'male' else "👩 Жінка"
        rating = user_data.get('rating', 5.0)
        profile_text = f"""👤 {title}

*Ім'я:* {user_data.get('first_name', 'Невідомо')}
*Вік:* {user_data.get('age', 'Не вказано')}
*Стать:* {gender_display}
*Місто:* {user_data.get('city', 'Не вказано')}
*Ціль:* {user_data.get('goal', 'Не вказано')}
*Про себе:* {user_data.get('bio', 'Не вказано')}
*Рейтинг:* ⭐ {rating:.1f}/10.0

💌 Натисни /like щоб лайкнути або /dislike щоб пропустити"""
    else:
        # Якщо user_data - кортеж (з бази даних)
        gender_display = "👨 Чоловік" if user_data[5] == 'male' else "👩 Жінка"
        rating = user_data[14] if len(user_data) > 14 else 5.0  # Індекс рейтингу
        profile_text = f"""👤 {title}

*Ім'я:* {user_data[3] if user_data[3] else 'Невідомо'}
*Вік:* {user_data[4] if user_data[4] else 'Не вказано'}
*Стать:* {gender_display}
*Місто:* {user_data[6] if user_data[6] else 'Не вказано'}
*Ціль:* {user_data[8] if user_data[8] else 'Не вказано'}
*Про себе:* {user_data[9] if user_data[9] else 'Не вказано'}
*Рейтинг:* ⭐ {rating:.1f}/10.0

💌 Натисни /like щоб лайкнути або /dislike щоб пропустити"""
    
    return profile_text

async def show_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data, title=""):
    """Показати профіль користувача"""
    try:
        chat_id = update.effective_chat.id
        
        # Отримуємо фото користувача
        if isinstance(user_data, dict):
            telegram_id = user_data.get('telegram_id')
        else:
            telegram_id = user_data[1]  # Індекс telegram_id
        
        photos = db.get_profile_photos(telegram_id)
        
        if photos:
            # Відправляємо перше фото
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photos[0],
                caption=format_profile_text(user_data, title),
                parse_mode='Markdown',
                reply_markup=get_search_navigation()
            )
            
            # Якщо є додаткові фото, відправляємо їх окремо
            for i, photo in enumerate(photos[1:], 1):
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=f"Фото {i+1}"
                )
        else:
            # Якщо фото немає
            await context.bot.send_message(
                chat_id=chat_id,
                text=format_profile_text(user_data, title),
                parse_mode='Markdown',
                reply_markup=get_search_navigation()
            )
            
    except Exception as e:
        print(f"❌ Помилка показу профілю: {e}")
        await update.message.reply_text(
            "❌ Помилка завантаження профілю. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def search_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук випадкового користувача"""
    try:
        user_id = update.effective_user.id
        
        # Перевіряємо чи заповнений профіль
        user, is_completed = db.get_user_profile(user_id)
        if not is_completed:
            await update.message.reply_text(
                "❌ Спочатку заповніть свій профіль!",
                reply_markup=get_main_menu()
            )
            return
        
        # Отримуємо випадкового користувача
        random_user = db.get_random_user(user_id)
        
        if random_user:
            user_states[user_id] = {
                'current_profile': random_user,
                'search_type': 'random'
            }
            
            await show_user_profile(update, context, random_user, "Знайомтесь!")
        else:
            await update.message.reply_text(
                "❌ Наразі немає користувачів для пошуку. Спробуйте пізніше.",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        print(f"❌ Помилка пошуку: {e}")
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def search_by_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошук за містом"""
    try:
        user_id = update.effective_user.id
        
        # Перевіряємо чи заповнений профіль
        user, is_completed = db.get_user_profile(user_id)
        if not is_completed:
            await update.message.reply_text(
                "❌ Спочатку заповніть свій профіль!",
                reply_markup=get_main_menu()
            )
            return
        
        # Отримуємо місто користувача
        user_data = db.get_user(user_id)
        if user_data and user_data.get('city'):
            city = user_data.get('city')
            await update.message.reply_text(f"🔍 Шукаємо в вашому місті: {city}")
            
            # Пошук у місті користувача
            users = db.get_users_by_city(city, user_id)
            
            if users:
                user_states[user_id] = {
                    'current_profile': users[0],
                    'search_results': users,
                    'current_index': 0,
                    'search_type': 'city'
                }
                
                await show_user_profile(update, context, users[0], f"Знайомтесь у місті {city}!")
            else:
                await update.message.reply_text(
                    f"❌ У вашому місті {city} поки немає інших користувачів.",
                    reply_markup=get_main_menu()
                )
        else:
            await update.message.reply_text(
                "❌ У вашому профілі не вказано місто. Спочатку заповніть профіль повністю.",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        print(f"❌ Помилка пошуку за містом: {e}")
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def search_by_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка введення міста для пошуку"""
    try:
        user_id = update.effective_user.id
        city = update.message.text
        
        # Перевіряємо чи заповнений профіль
        user, is_completed = db.get_user_profile(user_id)
        if not is_completed:
            await update.message.reply_text(
                "❌ Спочатку заповніть свій профіль!",
                reply_markup=get_main_menu()
            )
            return
        
        await update.message.reply_text(f"🔍 Шукаємо в місті: {city}")
        
        # Пошук у вказаному місті
        users = db.get_users_by_city(city, user_id)
        
        if users:
            user_states[user_id] = {
                'current_profile': users[0],
                'search_results': users,
                'current_index': 0,
                'search_type': 'city_input'
            }
            
            await show_user_profile(update, context, users[0], f"Знайомтесь у місті {city}!")
        else:
            await update.message.reply_text(
                f"❌ У місті {city} поки немає користувачів.",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        print(f"❌ Помилка пошуку за містом: {e}")
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Наступний профіль у пошуку"""
    try:
        user_id = update.effective_user.id
        state = user_states.get(user_id, {})
        
        if not state or 'search_type' not in state:
            await update.message.reply_text(
                "❌ Спочатку почніть пошук!",
                reply_markup=get_main_menu()
            )
            return
        
        search_type = state.get('search_type')
        
        if search_type == 'random':
            # Для випадкового пошуку - отримуємо нового випадкового користувача
            random_user = db.get_random_user(user_id)
            
            if random_user:
                user_states[user_id]['current_profile'] = random_user
                await show_user_profile(update, context, random_user, "Знайомтесь!")
            else:
                await update.message.reply_text(
                    "❌ Наразі немає більше користувачів для пошуку.",
                    reply_markup=get_main_menu()
                )
        
        elif search_type in ['city', 'city_input', 'advanced']:
            # Для пошуку з результатами - переходимо до наступного
            results = state.get('search_results', [])
            current_index = state.get('current_index', 0)
            
            if current_index < len(results) - 1:
                next_index = current_index + 1
                user_states[user_id]['current_index'] = next_index
                user_states[user_id]['current_profile'] = results[next_index]
                
                await show_user_profile(update, context, results[next_index], "Наступний профіль")
            else:
                await update.message.reply_text(
                    "❌ Це останній профіль у пошуку.",
                    reply_markup=get_search_navigation()
                )
        
        else:
            await update.message.reply_text(
                "❌ Невідомий тип пошуку.",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        print(f"❌ Помилка переходу до наступного профілю: {e}")
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def previous_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Попередній профіль у пошуку"""
    try:
        user_id = update.effective_user.id
        state = user_states.get(user_id, {})
        
        if not state or 'search_type' not in state:
            await update.message.reply_text(
                "❌ Спочатку почніть пошук!",
                reply_markup=get_main_menu()
            )
            return
        
        search_type = state.get('search_type')
        
        if search_type in ['city', 'city_input', 'advanced']:
            results = state.get('search_results', [])
            current_index = state.get('current_index', 0)
            
            if current_index > 0:
                prev_index = current_index - 1
                user_states[user_id]['current_index'] = prev_index
                user_states[user_id]['current_profile'] = results[prev_index]
                
                await show_user_profile(update, context, results[prev_index], "Попередній профіль")
            else:
                await update.message.reply_text(
                    "❌ Це перший профіль у пошуку.",
                    reply_markup=get_search_navigation()
                )
        else:
            await update.message.reply_text(
                "❌ Для випадкового пошуку немає попередніх профілів.",
                reply_markup=get_search_navigation()
            )
            
    except Exception as e:
        print(f"❌ Помилка переходу до попереднього профілю: {e}")
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка лайку"""
    try:
        user_id = update.effective_user.id
        state = user_states.get(user_id, {})
        
        if not state or 'current_profile' not in state:
            await update.message.reply_text(
                "❌ Спочатку виберіть користувача для лайку!",
                reply_markup=get_main_menu()
            )
            return
        
        current_profile = state['current_profile']
        
        if isinstance(current_profile, dict):
            to_user_id = current_profile.get('telegram_id')
        else:
            to_user_id = current_profile[1]  # Індекс telegram_id
        
        # Перевіряємо чи не лайкаємо самі себе
        if user_id == to_user_id:
            await update.message.reply_text(
                "❌ Ви не можете лайкнути самого себе!",
                reply_markup=get_search_navigation()
            )
            return
        
        # Додаємо лайк
        success, message = db.add_like(user_id, to_user_id)
        
        if success:
            # Перевіряємо чи це взаємний лайк
            if db.has_liked(to_user_id, user_id):
                match_message = "🎉 У вас взаємний лайк! Тепер ви можете спілкуватися."
                await update.message.reply_text(match_message)
                
                # Відправляємо сповіщення іншому користувачу
                await notification_system.send_match_notification(context.bot, user_id, to_user_id)
            
            await update.message.reply_text(
                f"✅ {message}",
                reply_markup=get_search_navigation()
            )
        else:
            await update.message.reply_text(
                f"❌ {message}",
                reply_markup=get_search_navigation()
            )
            
    except Exception as e:
        print(f"❌ Помилка лайку: {e}")
        await update.message.reply_text(
            "❌ Помилка лайку. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def handle_dislike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка дізлайку (пропуск)"""
    try:
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "👌 Користувача пропущено",
            reply_markup=get_search_navigation()
        )
        
        # Автоматично переходимо до наступного профілю
        await next_profile(update, context)
        
    except Exception as e:
        print(f"❌ Помилка дізлайку: {e}")
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def advanced_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню розширеного пошуку"""
    try:
        user_id = update.effective_user.id
        
        # Перевіряємо чи заповнений профіль
        user, is_completed = db.get_user_profile(user_id)
        if not is_completed:
            await update.message.reply_text(
                "❌ Спочатку заповніть свій профіль!",
                reply_markup=get_main_menu()
            )
            return
        
        # Встановлюємо стан для розширеного пошуку
        user_states[user_id] = {
            'state': States.ADVANCED_SEARCH_GENDER
        }
        
        await update.message.reply_text(
            "🔍 *Розширений пошук*\n\n"
            "Оберіть стать для пошуку:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([
                ["👨 Чоловіки", "👩 Жінки"],
                ["👥 Всі", "🔙 Назад"]
            ], resize_keyboard=True)
        )
        
    except Exception as e:
        print(f"❌ Помилка меню розширеного пошуку: {e}")
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def advanced_search_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору статі для розширеного пошуку"""
    try:
        user_id = update.effective_user.id
        gender_choice = update.message.text
        
        gender_map = {
            "👨 Чоловіки": "male",
            "👩 Жінки": "female",
            "👥 Всі": "all"
        }
        
        if gender_choice not in gender_map:
            await update.message.reply_text(
                "❌ Будь ласка, оберіть стать з клавіатури:",
                reply_markup=ReplyKeyboardMarkup([
                    ["👨 Чоловіки", "👩 Жінки"],
                    ["👥 Всі", "🔙 Назад"]
                ], resize_keyboard=True)
            )
            return
        
        if gender_choice == "🔙 Назад":
            user_states[user_id] = {}
            await update.message.reply_text(
                "🔙 Повертаємось до головного меню",
                reply_markup=get_main_menu()
            )
            return
        
        # Зберігаємо вибір статі
        context.user_data['advanced_search_gender'] = gender_map[gender_choice]
        
        # Переходимо до вибору міста
        user_states[user_id] = {
            'state': States.ADVANCED_SEARCH_CITY
        }
        
        await update.message.reply_text(
            "🏙️ Введіть місто для пошуку (або натисніть 'Пропустити'):",
            reply_markup=ReplyKeyboardMarkup([
                ["Пропустити", "🔙 Назад"]
            ], resize_keyboard=True)
        )
        
    except Exception as e:
        print(f"❌ Помилка вибору статі: {e}")
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def advanced_search_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка введення міста для розширеного пошуку"""
    try:
        user_id = update.effective_user.id
        city_input = update.message.text
        
        if city_input == "🔙 Назад":
            # Повертаємось до вибору статі
            user_states[user_id] = {
                'state': States.ADVANCED_SEARCH_GENDER
            }
            
            await update.message.reply_text(
                "🔍 Оберіть стать для пошуку:",
                reply_markup=ReplyKeyboardMarkup([
                    ["👨 Чоловіки", "👩 Жінки"],
                    ["👥 Всі", "🔙 Назад"]
                ], resize_keyboard=True)
            )
            return
        
        if city_input == "Пропустити":
            city = None
        else:
            city = city_input
        
        # Зберігаємо місто
        context.user_data['advanced_search_city'] = city
        
        # Переходимо до вибору цілі
        user_states[user_id] = {
            'state': States.ADVANCED_SEARCH_GOAL
        }
        
        await update.message.reply_text(
            "🎯 Оберіть ціль для пошуку:",
            reply_markup=ReplyKeyboardMarkup([
                ["💕 Серйозні стосунки", "💬 Дружба"],
                ["🎉 Несерйозні стосунки", "🤷 Поки не знаю"],
                ["Пропустити", "🔙 Назад"]
            ], resize_keyboard=True)
        )
        
    except Exception as e:
        print(f"❌ Помилка введення міста: {e}")
        await update.message.reply_text(
            "❌ Помилка. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def advanced_search_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка вибору цілі для розширеного пошуку"""
    try:
        user_id = update.effective_user.id
        goal_input = update.message.text
        
        goal_map = {
            "💕 Серйозні стосунки": "serious",
            "💬 Дружба": "friendship", 
            "🎉 Несерйозні стосунки": "casual",
            "🤷 Поки не знаю": "unknown",
            "Пропустити": None
        }
        
        if goal_input == "🔙 Назад":
            # Повертаємось до введення міста
            user_states[user_id] = {
                'state': States.ADVANCED_SEARCH_CITY
            }
            
            await update.message.reply_text(
                "🏙️ Введіть місто для пошуку (або натисніть 'Пропустити'):",
                reply_markup=ReplyKeyboardMarkup([
                    ["Пропустити", "🔙 Назад"]
                ], resize_keyboard=True)
            )
            return
        
        if goal_input not in goal_map:
            await update.message.reply_text(
                "❌ Будь ласка, оберіть ціль з клавіатури:",
                reply_markup=ReplyKeyboardMarkup([
                    ["💕 Серйозні стосунки", "💬 Дружба"],
                    ["🎉 Несерйозні стосунки", "🤷 Поки не знаю"],
                    ["Пропустити", "🔙 Назад"]
                ], resize_keyboard=True)
            )
            return
        
        # Отримуємо параметри пошуку
        gender = context.user_data.get('advanced_search_gender', 'all')
        city = context.user_data.get('advanced_search_city')
        goal = goal_map[goal_input]
        
        # Виконуємо пошук
        users = db.search_users_advanced(user_id, gender, city, goal)
        
        if users:
            user_states[user_id] = {
                'current_profile': users[0],
                'search_results': users,
                'current_index': 0,
                'search_type': 'advanced'
            }
            
            # Формуємо опис параметрів пошуку
            search_desc = "🔍 Розширений пошук\n"
            search_desc += f"Стать: {gender if gender != 'all' else 'Всі'}\n"
            search_desc += f"Місто: {city if city else 'Будь-яке'}\n" 
            search_desc += f"Ціль: {goal_input if goal_input != 'Пропустити' else 'Будь-яка'}"
            
            await show_user_profile(update, context, users[0], search_desc)
        else:
            await update.message.reply_text(
                "❌ За вашими критеріями не знайдено користувачів.",
                reply_markup=get_main_menu()
            )
        
        # Очищаємо тимчасові дані
        context.user_data.pop('advanced_search_gender', None)
        context.user_data.pop('advanced_search_city', None)
        
    except Exception as e:
        print(f"❌ Помилка вибору цілі: {e}")
        await update.message.reply_text(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )