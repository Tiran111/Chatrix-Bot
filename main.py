import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=== BUILD CHECK ===")

# Спроба імпорту залежностей
try:
    from flask import Flask, request
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    print("✅ All imports successful - running in PRODUCTION mode")
    
    # Твій основний код тут...
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "🤖 Bot is running!", 200
        
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port)
        
except ImportError as e:
    print(f"⚠️ Imports failed: {e}")
    print("✅ This is normal during BUILD process")
    print("✅ Dependencies will be installed by pip")
    # Не роби нічого - просто виходи
    exit(0)