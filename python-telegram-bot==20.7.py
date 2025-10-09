from database.models import db

def debug_top_users():
    print("🔍 ВІДЛАДКА ТОП КОРИСТУВАЧІВ")
    print("=" * 50)
    
    # Перевірка загального топу
    top_users = db.get_top_users_by_rating(limit=10)
    print(f"📊 Загальний топ: {len(top_users)} користувачів")
    
    for i, user in enumerate(top_users, 1):
        print(f"{i}. ID: {user[1]}, Ім'я: {user[3]}, Рейтинг: {user[14]}, Фото: {user[10]}")
    
    print("\n" + "=" * 50)
    
    # Перевірка ваших тестових профілів
    test_user_id = 1385645772  # Замініть на ID вашого тестового профілю
    print(f"🔍 Відладка тестового профілю {test_user_id}:")
    db.debug_user_profile(test_user_id)

if __name__ == "__main__":
    debug_top_users()