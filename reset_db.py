import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def reset_database():
    """Скидання та перестворення бази даних"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL не встановлено")
        return
    
    try:
        # Підключаємося до бази даних
        conn = psycopg2.connect(database_url, sslmode='require')
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Видаляємо всі таблиці
        tables = ['profile_views', 'matches', 'likes', 'photos', 'users']
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
                print(f"✅ Таблиця {table} видалена")
            except Exception as e:
                print(f"⚠️ Помилка видалення {table}: {e}")
        
        print("✅ База даних скинута. Перезапустіть бота для створення нових таблиць.")
        
    except Exception as e:
        print(f"❌ Помилка скидання бази даних: {e}")

if __name__ == '__main__':
    reset_database()