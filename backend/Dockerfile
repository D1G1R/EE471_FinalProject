# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Azure Speech SDK bağımlılıkları
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libasound2 \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

CMD ["gunicorn", "voice_controller.wsgi:application", "--bind", "0.0.0.0:8000"]