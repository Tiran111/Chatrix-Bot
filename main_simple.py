import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Налаштування
logging.basicConfig(level=logging.INFO)
TOKEN = "7823150178:AAElnZEQB9nSwJxAZ_J75Mg-1UVaVWQcr-s"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот працює! 🎉")

async def main():
    """Головна асинхронна функція"""
    print("🚀 Запуск бота...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        print("✅ Бот запущено! Очікування повідомлень...")
        
        # Запускаємо polling
        await application.run_polling()
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Запускаємо асинхронну функцію
    asyncio.run(main())