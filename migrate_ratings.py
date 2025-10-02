from database.models import db

def migrate_all_ratings():
    """Міграція рейтингів для всіх користувачів"""
    print("🔄 Запуск міграції рейтингів...")
    
    # Отримуємо всіх користувачів
    all_users = db.get_all_users()
    print(f"🔍 Знайдено {len(all_users)} користувачів для міграції")
    
    migrated = 0
    for user_id in all_users:
        try:
            rating = db.calculate_user_rating(user_id)
            migrated += 1
            if migrated % 50 == 0 or migrated == len(all_users):
                print(f"✅ Мігровано {migrated}/{len(all_users)} користувачів")
        except Exception as e:
            print(f"❌ Помилка міграції для {user_id}: {e}")
    
    print(f"🎉 Міграція завершена! Оброблено {migrated} користувачів")

if __name__ == '__main__':
    migrate_all_ratings()