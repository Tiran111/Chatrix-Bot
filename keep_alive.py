import requests
import time
import threading
import logging

logger = logging.getLogger(__name__)

class KeepAlive:
    def __init__(self, url="https://chatrix-bot-4m1p.onrender.com", interval=300):  # 5 хвилин
        self.url = url
        self.interval = interval
        self.is_running = False
        self.thread = None
    
    def start(self):
        """Запуск пінгування"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info(f"🚀 Keep-alive запущено з інтервалом {self.interval} секунд")
    
    def stop(self):
        """Зупинка пінгування"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        logger.info("🛑 Keep-alive зупинено")
    
    def _ping_loop(self):
        """Цикл пінгування"""
        while self.is_running:
            try:
                response = requests.get(self.url, timeout=10)
                if response.status_code == 200:
                    logger.info("✅ Keep-alive ping successful")
                else:
                    logger.warning(f"⚠️ Keep-alive ping returned status: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Keep-alive ping failed: {e}")
            
            time.sleep(self.interval)

# Глобальний екземпляр
keep_alive = KeepAlive()

def start_keep_alive():
    """Запуск keep-alive"""
    keep_alive.start()

def stop_keep_alive():
    """Зупинка keep-alive"""
    keep_alive.stop()