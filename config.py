import os

# Для дебагу - виведемо всі змінні середовища
print("🔧 Перевірка змінних середовища:")
all_vars = dict(os.environ)
for key, value in all_vars.items():
    if 'BOT' in key or 'TOKEN' in key or 'ADMIN' in key:
        print(f"   {key}: {value[:10]}...")  # Показуємо тільки початок для безпеки

# Отримуємо токен
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')

if not TOKEN:
    print("❌ ТОКЕН НЕ ЗНАЙДЕНО! Доступні змінні:")
    for key in all_vars.keys():
        print(f"   - {key}")
    raise ValueError("TELEGRAM_BOT_TOKEN не знайдено в змінних середовища!")

ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

# DATABASE_URL не потрібен для SQLite
print(f"✅ Токен отримано, довжина: {len(TOKEN)}")
print(f"✅ ADMIN_ID: {ADMIN_ID}")