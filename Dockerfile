FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Використовуємо gunicorn для стабільності
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 main_webhook:app