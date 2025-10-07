import os

# Для дебагу
print("🔧 Перевірка змінних середовища:")
for key in ['TELEGRAM_BOT_TOKEN', 'BOT_TOKEN', 'TOKEN']:
    value = os.getenv(key)
    print(f"   {key}: {'✅ Знайдено' if value else '❌ Відсутній'}")

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    print("❌ Токен не знайдено! Доступні змінні:")
    for key, value in os.environ.items():
        print(f"   {key}: {value}")
    raise ValueError("TELEGRAM_BOT_TOKEN не знайдено!")

ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')