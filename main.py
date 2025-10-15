import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from config import BOT_TOKEN, ADMIN_ID
from database.models import db
from keyboards.main_menu import get_main_menu, get_rating_keyboard, get_back_to_menu_keyboard
from utils.states import user_states, States
from handlers.profile_handlers import handle_photo, handle_text, show_profile, handle_delete_photo
from handlers.rating_handlers import handle_like, handle_dislike, show_random_profile, handle_skip
from handlers.match_handlers import handle_matches, show_match_details
from handlers.admin_handlers import admin_panel, show_statistics, broadcast_message, handle_broadcast_text
from utils.helpers import send_notification, validate_user, cleanup_inactive_users

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
                "📞 <b>Підтримка:</b> @support_username"
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

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def main():
    """Основна функція запуску бота"""
    try:
        # Ініціалізація бази даних
        logger.info("🔄 Ініціалізація бази даних...")
        db.init_db()
        
        # Створюємо додаток
        application = Application.builder().token(BOT_TOKEN).build()
        
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
        application.add_handler(CallbackQueryHandler(show_match_details, pattern='^match_'))
        application.add_handler(CallbackQueryHandler(handle_delete_photo, pattern='^delete_photo_'))
        application.add_handler(CallbackQueryHandler(broadcast_message, pattern='^broadcast$'))
        
        # Додаємо обробники повідомлень
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
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
        db.conn.close()
        logger.info("🔴 Бот зупинений")

if __name__ == '__main__':
    main()