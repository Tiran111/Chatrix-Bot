from main import app, start_polling
import threading

# Запускаємо полінг в окремому потоці
polling_thread = threading.Thread(target=start_polling, daemon=True)
polling_thread.start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)