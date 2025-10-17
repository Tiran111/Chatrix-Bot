import os

# Змінні середовища
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

def initialize_config():
    """Ініціалізація конфігурації"""
    if not TOKEN or TOKEN == 'your_bot_token_here':
        raise ValueError("❌ BOT_TOKEN не встановлено або встановлено тестове значення")
    
    if ADMIN_ID == 0:
        raise ValueError("❌ ADMIN_ID не встановлено")
    
    print("✅ Конфігурація успішно ініціалізована")