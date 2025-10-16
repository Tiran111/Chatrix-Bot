import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from config import initialize_config, TOKEN, ADMIN_ID
from database.models import db
from keyboards.main_menu import get_main_menu, get_back_to_menu_keyboard
from utils.states import user_states, States

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    try:
        user = update.effective_user
        chat = update.effective_chat
        
        logger.info(f"🆕 Користувач: {user.first_name} (ID: {user.id}) викликав /start в чаті {chat.id}")
        
        # Додаємо/оновлюємо користувача в базі даних
        success = db.add_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        if not success:
            logger.error(f"❌ Не вдалося додати/оновити користувача {user.id} в базі даних")
            await update.message.reply_text(
                "❌ Помилка реєстрації. Будь ласка, спробуйте ще раз через кілька хвилин."
            )
            return
        
        logger.info(f"✅ Користувач {user.id} успішно доданий/оновлений в базі даних")
        
        # Оновлюємо стан користувача
        user_states[user.id] = States.START
        
        # Відправляємо привітальне повідомлення
        welcome_text = (
            f"👋 Вітаю, {user.first_name}!\n\n"
            "💫 <b>Ласкаво просимо до спільноти знайомств!</b>\n\n"
            "🌟 <b>Що ти можеш робити:</b>\n"
            "📸 • Додавати до 3 фото у свій профіль\n"
            "💞 • Оцінювати анкети інших людей\n"
            "🤝 • Знаходити матчі (взаємні лайки)\n"
            "👤 • Налаштовувати свій профіль\n"
            "📊 • Переглядати свою статистику\n\n"
            "🎯 <b>Як це працює:</b>\n"
            "1. Додай фото для привернення уваги\n"
            "2. Оцінюй інших користувачів\n"
            "3. Знаходь матчі та спілкуйся\n"
            "4. Підвищуй свій рейтинг\n\n"
            "💡 <b>Порада:</b> Чим якісніші фото, тим більше лайків отримаєш!"
        )
        
        # Відправляємо повідомлення з головним меню
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu(),
            parse_mode='HTML'
        )
        
        # Відправляємо сповіщення адміну про нового користувача
        if ADMIN_ID:
            admin_notification = (
                f"🆕 Новий користувач:\n"
                f"👤 Ім'я: {user.first_name}\n"
                f"🆔 ID: {user.id}\n"
                f"📛 Username: @{user.username if user.username else 'Немає'}\n"
                f"📅 Зареєстровано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await context.bot.send_message(ADMIN_ID, admin_notification)
            
    except Exception as e:
        logger.error(f"❌ Критична помилка в функції start: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                "❌ Сталася критична помилка. Будь ласка, спробуйте ще раз або зверніться до підтримки."
            )
        except Exception:
            pass

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати профіль користувача"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        # Отримуємо дані користувача
        user = db.get_user(user_id)
        if not user:
            await query.edit_message_text(
                "❌ Не вдалося завантажити профіль",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        # Отримуємо фото користувача
        photos = db.get_profile_photos(user_id)
        
        # Формуємо текст профілю
        profile_text = (
            f"👤 <b>Ваш профіль</b>\n\n"
            f"🆔 ID: {user['telegram_id']}\n"
            f"📛 Ім'я: {user['first_name']}\n"
            f"👤 Username: @{user['username'] if user['username'] else 'Немає'}\n"
            f"📸 Фото: {len(photos)}/3\n"
            f"❤️ Рейтинг: {user.get('rating', 5.0):.1f}\n"
            f"👍 Отримано лайків: {user.get('likes_count', 0)}\n"
            f"🤝 Матчі: {len(db.get_user_matches(user_id))}\n"
        )
        
        if user.get('age'):
            profile_text += f"🎂 Вік: {user['age']}\n"
        if user.get('gender'):
            gender_display = "👨 Чоловік" if user['gender'] == 'male' else "👩 Жінка"
            profile_text += f"⚧️ Стать: {gender_display}\n"
        if user.get('city'):
            profile_text += f"🏙️ Місто: {user['city']}\n"
        if user.get('goal'):
            profile_text += f"🎯 Ціль: {user['goal']}\n"
        
        profile_text += f"📅 Реєстрація: {user.get('created_at', 'Невідомо')[:10]}\n"
        profile_text += f"🕐 Остання активність: {user.get('last_active', 'Невідомо')[:16]}\n"
        
        # Додаємо біографію якщо є
        if user.get('bio'):
            profile_text += f"\n📝 <b>Про себе:</b>\n{user['bio']}\n"
        
        # Створюємо клавіатуру для управління профілем
        keyboard = []
        
        if photos:
            keyboard.append([InlineKeyboardButton("🗑️ Видалити фото", callback_data="delete_photos")])
        
        if len(photos) < 3:
            keyboard.append([InlineKeyboardButton("📸 Додати фото", callback_data="add_photo")])
        
        keyboard.extend([
            [InlineKeyboardButton("📊 Статистика", callback_data="my_rating")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Відправляємо повідомлення
        await query.edit_message_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка показу профілю: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                "❌ Помилка завантаження профілю",
                reply_markup=get_back_to_menu_keyboard()
            )
        except Exception:
            pass

async def show_random_profile(user_id, context, message):
    """Показати випадковий профіль для оцінки"""
    try:
        # Отримуємо випадкового користувача
        random_user = db.get_random_user(user_id)
        
        if not random_user:
            await message.edit_text(
                "😔 Наразі немає анкет для перегляду.\nСпробуйте пізніше!",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        # Форматуємо профіль
        profile_text = format_profile_text(random_user, "💕 Знайдені анкети")
        
        # Створюємо клавіатуру для оцінки
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{random_user[1]}"),
             InlineKeyboardButton("👎 Дизлайк", callback_data=f"dislike_{random_user[1]}")],
            [InlineKeyboardButton("➡️ Пропустити", callback_data=f"skip_{random_user[1]}"),
             InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]
        ])
        
        # Отримуємо фото користувача
        main_photo = db.get_main_photo(random_user[1])
        
        if main_photo:
            await message.reply_photo(
                photo=main_photo,
                caption=profile_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await message.reply_text(
                profile_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка показу випадкового профілю: {e}")
        await message.edit_text(
            "❌ Помилка завантаження профілю. Спробуйте ще раз.",
            reply_markup=get_back_to_menu_keyboard()
        )

def format_profile_text(user_data, title=""):
    """Форматування тексту профілю"""
    try:
        gender_display = "👨 Чоловік" if user_data[5] == 'male' else "👩 Жінка"
        
        profile_text = f"""👤 {title}

*Ім'я:* {user_data[3]}
*Вік:* {user_data[4]} років
*Стать:* {gender_display}
*Місто:* {user_data[6]}
*Ціль:* {user_data[8]}

*Про себе:*
{user_data[9] if user_data[9] else "Не вказано"}"""
        
        return profile_text
    except Exception as e:
        logger.error(f"❌ Помилка форматування профілю: {e}")
        return "❌ Помилка завантаження профілю"

async def handle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник лайку"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        target_user_id = int(query.data.split('_')[1])
        
        # Додаємо лайк
        success, message = db.add_like(user_id, target_user_id)
        
        if success:
            # Перевіряємо чи це взаємний лайк
            if db.has_liked(target_user_id, user_id):
                # Матч!
                target_user = db.get_user(target_user_id)
                if target_user and target_user.get('username'):
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💬 Написати в Telegram", url=f"https://t.me/{target_user['username']}")]
                    ])
                    await query.edit_message_text(
                        "💕 У вас матч! Ви вподобали один одного!\n\n"
                        "💬 Тепер ви можете почати спілкування!",
                        reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text("💕 У вас матч! Ви вподобали один одного!")
            else:
                await query.edit_message_text(f"❤️ {message}")
        else:
            await query.edit_message_text(f"❌ {message}")
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки лайку: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Помилка при обробці лайку.")
        except:
            pass

async def handle_dislike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник дизлайку"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        target_user_id = int(query.data.split('_')[1])
        
        # Просто показуємо наступний профіль
        await show_random_profile(user_id, context, query.message)
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки дизлайку: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Помилка при обробці дизлайку.")
        except:
            pass

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник пропуску"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await show_random_profile(user_id, context, query.message)
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки пропуску: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Помилка при обробці пропуску.")
        except:
            pass

async def handle_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати матчі користувача"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        matches = db.get_user_matches(user_id)
        
        if matches:
            match_text = f"💌 <b>Ваші матчі ({len(matches)}):</b>\n\n"
            
            for i, match in enumerate(matches, 1):
                match_user = db.get_user(match[1])
                if match_user:
                    username = f"@{match_user['username']}" if match_user.get('username') else "немає username"
                    match_text += f"{i}. {match_user['first_name']} ({username})\n"
            
            await query.edit_message_text(
                match_text,
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "😔 У вас ще немає матчів.\n\n"
                "💡 Активніше оцінюйте інших користувачів, щоб знайти матч!",
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode='HTML'
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка показу матчів: {e}")
        await query.edit_message_text(
            "❌ Помилка завантаження матчів",
            reply_markup=get_back_to_menu_keyboard()
        )

async def handle_delete_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник видалення фото"""
    try:
        query = update.callback_query
        await query.answer("Функція видалення фото буде реалізована найближчим часом!")
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки видалення фото: {e}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Адмін панель"""
    try:
        user = update.effective_user
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ заборонено")
            return
            
        stats = db.get_statistics()
        male, female, total_active, goals_stats = stats
        
        stats_text = f"""📊 <b>Статистика бота</b>

👥 Загалом користувачів: {db.get_users_count()}
✅ Активних анкет: {total_active}
👨 Чоловіків: {male}
👩 Жінок: {female}"""

        await update.message.reply_text(
            stats_text,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка адмін панелі: {e}")

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показати статистику"""
    try:
        user = update.effective_user
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ заборонено")
            return
            
        await admin_panel(update, context)
        
    except Exception as e:
        logger.error(f"❌ Помилка статистики: {e}")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Розсилка повідомлень"""
    try:
        query = update.callback_query
        await query.answer("Функція розсилки буде реалізована найближчим часом!")
        
    except Exception as e:
        logger.error(f"❌ Помилка розсилки: {e}")

async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка тексту для розсилки"""
    try:
        user = update.effective_user
        if user.id != ADMIN_ID:
            return
            
        await update.message.reply_text("Функція розсилки буде реалізована найближчим часом!")
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки розсилки: {e}")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник головного меню"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        logger.info(f"🔘 Користувач {user_id} обрав пункт меню: {data}")
        
        # Оновлюємо останню активність
        db.cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?', (user_id,))
        db.conn.commit()
        
        if data == 'add_photo':
            user_states[user_id] = States.ADDING_PHOTO
            current_photos = db.get_profile_photos(user_id)
            
            photo_text = (
                f"📸 <b>Додавання фото</b>\n\n"
                f"Зараз у вашому профілі: <b>{len(current_photos)}/3</b> фото\n\n"
            )
            
            if len(current_photos) < 3:
                photo_text += (
                    "Надішліть фото для вашого профілю.\n"
                    "⚠️ <b>Вимоги до фото:</b>\n"
                    "• Чітке та якісне зображення\n"
                    "• Бажано на світлому фоні\n"
                    "• Особа має бути добре видно\n"
                    "• Без непристойного контенту\n\n"
                    "📎 Просто відправте фото у цей чат"
                )
            else:
                photo_text += (
                    "❌ Ви вже досягли максимальної кількості фото (3).\n"
                    "Щоб додати нове, спочатку видаліть одне з існуючих."
                )
            
            await query.edit_message_text(
                photo_text,
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode='HTML'
            )
            
        elif data == 'view_profile':
            await show_profile(update, context)
            
        elif data == 'rate_users':
            # Перевіряємо чи є фото у користувача
            user_photos = db.get_profile_photos(user_id)
            if not user_photos:
                await query.edit_message_text(
                    "❌ <b>Спочатку додайте фото до профілю!</b>\n\n"
                    "Щоб оцінювати інших користувачів, вам потрібно мати хоча б одне фото у своєму профілі.",
                    reply_markup=get_back_to_menu_keyboard(),
                    parse_mode='HTML'
                )
                return
                
            user_states[user_id] = States.RATING
            await show_random_profile(user_id, context, query.message)
            
        elif data == 'view_matches':
            await handle_matches(update, context)
            
        elif data == 'my_rating':
            user = db.get_user(user_id)
            if user:
                rating_text = (
                    f"📊 <b>Ваша статистика</b>\n\n"
                    f"❤️ <b>Загальний рейтинг:</b> {user.get('rating', 5.0):.1f}\n"
                    f"👍 <b>Отримано лайків:</b> {user.get('likes_count', 0)}\n"
                    f"🤝 <b>Кількість матчів:</b> {len(db.get_user_matches(user_id))}\n"
                    f"📅 <b>Реєстрація:</b> {user.get('created_at', 'Невідомо')[:10]}\n"
                    f"🕐 <b>Остання активність:</b> {user.get('last_active', 'Невідомо')[:16]}\n"
                )
                await query.edit_message_text(
                    rating_text,
                    reply_markup=get_back_to_menu_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text(
                    "❌ Не вдалося завантажити статистику",
                    reply_markup=get_back_to_menu_keyboard()
                )
                
        elif data == 'settings':
            await query.edit_message_text(
                "⚙️ <b>Налаштування</b>\n\n"
                "Оберіть опцію для налаштування:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Сповіщення", callback_data="notifications")],
                    [InlineKeyboardButton("👤 Редагувати профіль", callback_data="edit_profile")],
                    [InlineKeyboardButton("🗑️ Видалити акаунт", callback_data="delete_account")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]
                ]),
                parse_mode='HTML'
            )
            
        elif data == 'help':
            help_text = (
                "ℹ️ <b>Довідка по боту</b>\n\n"
                "📸 <b>Додати фото</b> - Додайте до 3 фото у ваш профіль\n"
                "💞 <b>Оцінювати</b> - Оцінюйте інших користувачів\n"
                "🤝 <b>Мої матчі</b> - Переглядайте взаємні лайки\n"
                "👤 <b>Мій профіль</b> - Переглядайте свій профіль\n"
                "📊 <b>Моя статистика</b> - Детальна статистика\n"
                "⚙️ <b>Налаштування</b> - Налаштування акаунта\n\n"
                "❓ <b>Часті питання:</b>\n"
                "• <b>Як знайти матч?</b> - Оцінюйте користувачів, при взаємному лайку буде матч\n"
                "• <b>Чому мене ніхто не оцінює?</b> - Додайте якісні фото та активуйтеся\n"
                "• <b>Як підвищити рейтинг?</b> - Отримуйте лайки від інших\n\n"
                "📞 <b>Підтримка:</b> Напишіть адміністратору"
            )
            await query.edit_message_text(
                help_text,
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode='HTML'
            )
            
        elif data == 'back_to_menu':
            user_states[user_id] = States.START
            await query.edit_message_text(
                "🔙 Повернулись до головного меню",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка в обробнику головного меню: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                "❌ Сталася помилка. Спробуйте ще раз.",
                reply_markup=get_main_menu()
            )
        except Exception:
            pass

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник отримання фото"""
    try:
        user = update.effective_user
        user_id = user.id
        state = user_states.get(user_id, States.START)
        
        if state == States.ADDING_PHOTO:
            # Отримуємо файл фото з найвищою якістю
            photo_file = await update.message.photo[-1].get_file()
            file_id = photo_file.file_id
            
            logger.info(f"📸 Отримано фото від {user_id}, file_id: {file_id}")
            
            # Додаємо фото до профілю
            success = db.add_profile_photo(user_id, file_id)
            
            if success:
                await update.message.reply_text(
                    "✅ Фото успішно додано до вашого профілю!",
                    reply_markup=get_main_menu()
                )
                # Оновлюємо стан
                user_states[user_id] = States.START
            else:
                await update.message.reply_text(
                    "❌ Не вдалося додати фото. Можливо, досягнуто ліміт (3 фото).",
                    reply_markup=get_main_menu()
                )
        else:
            await update.message.reply_text(
                "📸 Щоб додати фото, оберіть 'Додати фото' в головному меню 👇",
                reply_markup=get_main_menu()
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка обробки фото: {e}")
        await update.message.reply_text(
            "❌ Сталася помилка при обробці фото. Спробуйте ще раз.",
            reply_markup=get_main_menu()
        )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник текстових повідомлень"""
    try:
        user_id = update.effective_user.id
        text = update.message.text
        
        # Оновлюємо активність користувача
        db.cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?', (user_id,))
        db.conn.commit()
        
        await update.message.reply_text(
            "💬 Оберіть дію з головного меню 👇",
            reply_markup=get_main_menu()
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка обробки повідомлення: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    try:
        logger.error(f"❌ Помилка: {context.error}", exc_info=True)
        
        # Відправляємо повідомлення про помилку адміну
        if ADMIN_ID:
            error_message = (
                f"🚨 <b>Помилка в боті:</b>\n"
                f"🕐 Час: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📝 Деталі: {str(context.error)[:1000]}"
            )
            try:
                await context.bot.send_message(ADMIN_ID, error_message, parse_mode='HTML')
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"❌ Помилка в обробнику помилок: {e}")

async def periodic_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Періодичне очищення неактивних користувачів"""
    try:
        logger.info("🔄 Запуск періодичного очищення неактивних користувачів")
        # Викликаємо функцію очищення з models.py
        db.cleanup_old_data()
    except Exception as e:
        logger.error(f"❌ Помилка при очищенні неактивних користувачів: {e}")

async def post_init(application: Application):
    """Функція, яка викликається після ініціалізації бота"""
    logger.info("✅ Бот успішно ініціалізований на Render")

def main():
    """Основна функція запуску бота"""
    try:
        # Ініціалізація конфігурації
        logger.info("🔄 Ініціалізація конфігурації...")
        initialize_config()
        
        # Ініціалізація бази даних
        logger.info("🔄 Ініціалізація бази даних...")
        db.init_db()
        
        # Створюємо додаток
        application = Application.builder().token(TOKEN).post_init(post_init).build()
        
        # Додаємо обробник помилок
        application.add_error_handler(error_handler)
        
        # Додаємо обробники команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("stats", show_statistics))
        
        # Додаємо обробники callback-запитів
        application.add_handler(CallbackQueryHandler(handle_main_menu, pattern='^(add_photo|view_profile|rate_users|view_matches|my_rating|settings|help|back_to_menu)$'))
        application.add_handler(CallbackQueryHandler(handle_like, pattern='^like_'))
        application.add_handler(CallbackQueryHandler(handle_dislike, pattern='^dislike_'))
        application.add_handler(CallbackQueryHandler(handle_skip, pattern='^skip_'))
        application.add_handler(CallbackQueryHandler(handle_delete_photo, pattern='^delete_photo_'))
        application.add_handler(CallbackQueryHandler(broadcast_message, pattern='^broadcast$'))
        
        # Додаємо обробники повідомлень
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Додаємо обробник для broadcast
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^BRD:') & filters.User(ADMIN_ID), 
            handle_broadcast_text
        ))
        
        # Додаємо періодичні задачі
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(periodic_cleanup, interval=3600, first=10)  # Кожну годину
        
        logger.info("🤖 Бот запускається...")
        
        # Запускаємо бота
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            timeout=30
        )
        
    except Exception as e:
        logger.error(f"❌ Критична помилка запуску бота: {e}", exc_info=True)
    finally:
        # Завершуємо роботу з базою даних
        if hasattr(db, 'conn'):
            db.conn.close()
        logger.info("🔴 Бот зупинений")

if __name__ == '__main__':
    main()