from database.models import db
import logging

logger = logging.getLogger(__name__)

def debug_database():
    """Детальна діагностика бази даних"""
    logger.info("🔧 ЗАПУСК ДЕТАЛЬНОЇ ДІАГНОСТИКИ БАЗИ ДАНИХ")
    
    # Отримуємо всіх користувачів
    all_users = db.get_all_users()
    logger.info(f"🔧 Всього користувачів в базі: {len(all_users)}")
    
    for user in all_users:
        user_id = user[1] if len(user) > 1 else "N/A"
        username = user[2] if len(user) > 2 else "N/A"
        first_name = user[3] if len(user) > 3 else "N/A"
        age = user[4] if len(user) > 4 else "N/A"
        gender = user[5] if len(user) > 5 else "N/A"
        city = user[6] if len(user) > 6 else "N/A"
        seeking_gender = user[7] if len(user) > 7 else "N/A"
        has_photo = user[10] if len(user) > 10 else "N/A"
        
        logger.info(f"🔧 Користувач: ID={user_id}, Ім'я={first_name}, Вік={age}, Стать={gender}, Шукає={seeking_gender}, Фото={has_photo}")
    
    # Перевіряємо пошук для конкретних користувачів
    if len(all_users) >= 2:
        user1 = all_users[0]
        user2 = all_users[1]
        
        user1_id = user1[1]
        user2_id = user2[1]
        
        logger.info(f"🔧 Тестуємо пошук для {user1_id} (шукає {user1[7]})")
        result1 = db.get_random_user(user1_id)
        logger.info(f"🔧 Результат для {user1_id}: {'Знайдено' if result1 else 'Не знайдено'}")
        
        logger.info(f"🔧 Тестуємо пошук для {user2_id} (шукає {user2[7]})")
        result2 = db.get_random_user(user2_id)
        logger.info(f"🔧 Результат для {user2_id}: {'Знайдено' if result2 else 'Не знайдено'}")

# Запускаємо діагностику при імпорті
if __name__ == "__main__":
    debug_database()