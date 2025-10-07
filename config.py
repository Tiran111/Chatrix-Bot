import os

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"Token from env: {TOKEN}")  # Для дебагу

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не знайдено!")

ADMIN_ID = int(os.getenv('ADMIN_ID', '1385645772'))

GOALS = {
    '💞 Серйозні стосунки': 'Серйозні стосунки',
    '👥 Дружба': 'Дружба', 
    '🎉 Разові зустрічі': 'Разові зустрічі',
    '🏃 Активний відпочинок': 'Активний відпочинок'
}

DATABASE_URL = os.getenv('DATABASE_URL')