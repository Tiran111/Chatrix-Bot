from database.models import db
import sqlite3

def update_database_structure():
    """Оновлення структури бази даних"""
    print("🔄 Оновлення структури бази даних...")
    
    try:
        # Додаємо колонку rating до таблиці users
        db.cursor.execute('''
            ALTER TABLE users ADD COLUMN rating REAL DEFAULT 5.0
        ''')
        print("✅ Колонка 'rating' додана до таблиці users")
        
        # Додаємо колонки для обмеження лайків
        db.cursor.execute('''
            ALTER TABLE users ADD COLUMN daily_likes_count INTEGER DEFAULT 0
        ''')
        print("✅ Колонка 'daily_likes_count' додана до таблиці users")
        
        db.cursor.execute('''
            ALTER TABLE users ADD COLUMN last_like_date DATE
        ''')
        print("✅ Колонка 'last_like_date' додана до таблиці users")
        
        db.conn.commit()
        print("🎉 Структура бази даних оновлена успішно!")
        
        # Перевіряємо оновлення
        check_database_structure()
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ Колонки вже існують в базі даних")
        else:
            print(f"❌ Помилка оновлення бази даних: {e}")

def check_database_structure():
    """Перевірка структури бази даних"""
    print("\n🔍 Перевірка структури бази даних...")
    
    # Перевіряємо колонки таблиці users
    db.cursor.execute("PRAGMA table_info(users)")
    columns = db.cursor.fetchall()
    
    print("📋 Колонки таблиці users:")
    for column in columns:
        print(f"  - {column[1]} ({column[2]})")
    
    # Перевіряємо наявність тестових користувачів
    db.cursor.execute("SELECT COUNT(*) FROM users WHERE age IS NOT NULL AND has_photo = TRUE")
    active_users = db.cursor.fetchone()[0]
    print(f"\n👥 Активних користувачів: {active_users}")
    
    # Перевіряємо топ користувачів
    db.cursor.execute('''
        SELECT telegram_id, first_name, rating, likes_count 
        FROM users 
        WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE
        ORDER BY rating DESC, likes_count DESC 
        LIMIT 5
    ''')
    top_users = db.cursor.fetchall()
    
    print(f"\n🏆 Топ-5 користувачів:")
    for i, user in enumerate(top_users, 1):
        print(f"  {i}. {user[1]} (Рейтинг: {user[2]}, Лайків: {user[3]})")

def fix_user_ratings():
    """Оновлення рейтингів для всіх користувачів"""
    print("\n🔄 Оновлення рейтингів користувачів...")
    
    # Отримуємо всіх активних користувачів
    db.cursor.execute('''
        SELECT telegram_id FROM users 
        WHERE age IS NOT NULL AND has_photo = TRUE AND is_banned = FALSE
    ''')
    users = db.cursor.fetchall()
    
    updated_count = 0
    for user in users:
        telegram_id = user[0]
        new_rating = db.calculate_user_rating(telegram_id)
        
        db.cursor.execute(
            'UPDATE users SET rating = ? WHERE telegram_id = ?',
            (new_rating, telegram_id)
        )
        updated_count += 1
    
    db.conn.commit()
    print(f"✅ Рейтинги оновлено для {updated_count} користувачів")

if __name__ == "__main__":
    update_database_structure()
    fix_user_ratings()