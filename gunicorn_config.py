bind = "0.0.0.0:10000"
workers = 1
timeout = 120
preload_app = True
max_requests = 1000  # Перезапускати воркер після 1000 запитів
max_requests_jitter = 100  # Випадковий діапазон для уникнення одночасного перезапуску