FROM python:3.11-slim

WORKDIR /app

# Копіюємо requirements та встановлюємо бібліотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту файлів
COPY . .

CMD ["python", "main.py"]