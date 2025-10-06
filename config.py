import os

# Отримуємо змінні оточення
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Безпечне отримання ADMIN_ID з fallback значенням
try:
    ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))
except (TypeError, ValueError):
    ADMIN_ID = 1385645772  # Fallback значення

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')

# Додамо логування для дебагу
print(f"🔧 CONFIG: TOKEN = {'✅ Встановлено' if TOKEN else '❌ Відсутній'}")
print(f"🔧 CONFIG: ADMIN_ID = {ADMIN_ID}")
print(f"🔧 CONFIG: DATABASE_URL = {DATABASE_URL}")