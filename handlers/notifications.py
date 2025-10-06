from telegram import Update
from telegram.ext import ContextTypes
from database.models import db
from keyboards.main_menu import get_main_menu
import asyncio

class NotificationSystem:
    def __init__(self):
        self.pending_notifications = {}
    
    async def notify_new_like(self, context: ContextTypes.DEFAULT_TYPE, from_user_id, to_user_id):
        """Покращене сповіщення про лайк"""
        try:
            from_user = db.get_user(from_user_id)
            to_user = db.get_user(to_user_id)
            
            if not from_user or not to_user:
                return
            
            # Оновлюємо рейтинг отримувача
            db.update_rating_on_like(to_user_id)
            
            # Отримуємо актуальний рейтинг
            current_rating = db.calculate_user_rating(to_user_id)
            
            message = (
                f"💕 *У вас новий лайк!*\n\n"
                f"👤 *{from_user['first_name']}* вподобав(ла) вашу анкету!\n"
                f"⭐ *Ваш рейтинг:* {current_rating:.1f}/10.0\n\n"
                f"🎯 *Порада:* Активність підвищує ваш рейтинг!"
            )
            
            await context.bot.send_message(
                chat_id=to_user_id,
                text=message,
                parse_mode='Markdown'
            )
            print(f"✅ Покращене сповіщення про лайк відправлено {to_user_id}")
        except Exception as e:
            print(f"❌ Помилка покращеного сповіщення: {e}")
    
    async def notify_new_match(self, context: ContextTypes.DEFAULT_TYPE, user1_id, user2_id):
        """Сповістити про новий матч"""
        try:
            user1 = db.get_user(user1_id)
            user2 = db.get_user(user2_id)
            
            if user1 and user2:
                # Сповіщаємо першому користувачу
                await context.bot.send_message(
                    chat_id=user1_id,
                    text=f"💕 *У вас новий матч!*\n\nВи та {user2['first_name']} вподобали один одного!",
                    parse_mode='Markdown'
                )
                # Сповіщаємо другому користувачу
                await context.bot.send_message(
                    chat_id=user2_id,
                    text=f"💕 *У вас новий матч!*\n\nВи та {user1['first_name']} вподобали один одного!",
                    parse_mode='Markdown'
                )
                print(f"✅ Сповіщення про матч відправлено {user1_id} та {user2_id}")
        except Exception as e:
            print(f"❌ Помилка сповіщення про матч: {e}")

# Глобальний об'єкт системи сповіщень
notification_system = NotificationSystem()