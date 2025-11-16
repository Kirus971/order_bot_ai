# Быстрый деплой - Шпаргалка

## Если на сервере уже есть Git и Docker

### Шаг 1: Подключитесь к серверу
```bash
ssh root@178.xxx.xxx.xxx
```

### Шаг 2: Клонируйте проект
```bash
cd /opt
git clone <your-repo-url> order_bot
cd order_bot
```

### Шаг 3: Создайте .env файл
```bash
nano .env
```
Заполните все необходимые переменные (см. .env.example)

### Шаг 4: Запустите
```bash
docker compose up -d --build
```

### Шаг 5: Проверьте логи
```bash
docker compose logs -f
```

### Шаг 6: Настройте автозапуск (опционально)
```bash
# Создайте systemd service
sudo nano /etc/systemd/system/order-bot.service
```

Вставьте:
```ini
[Unit]
Description=Order Bot Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/order_bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

Активируйте:
```bash
sudo systemctl daemon-reload
sudo systemctl enable order-bot.service
sudo systemctl start order-bot.service
```

## Если нет Git репозитория

### Вариант A: Используйте скрипт деплоя (с локальной машины)
```bash
./deploy.sh root@178.xxx.xxx.xxx /opt/order_bot
```

### Вариант B: Вручную через SCP
```bash
# На локальной машине создайте архив
tar --exclude='.git' --exclude='__pycache__' --exclude='.env' --exclude='Untitled.ipynb' -czf order_bot.tar.gz .

# Скопируйте на сервер
scp order_bot.tar.gz root@178.xxx.xxx.xxx:/opt/

# На сервере
ssh root@178.xxx.xxx.xxx
cd /opt
mkdir -p order_bot
tar -xzf order_bot.tar.gz -C order_bot
cd order_bot
nano .env  # Создайте и заполните .env
docker compose up -d --build
```

## Настройка Webhook с Nginx (встроен в Docker)

Nginx уже включен в Docker Compose и автоматически настроен для балансировки нагрузки.

### 1. Для разработки (самоподписанный сертификат)

Сертификат генерируется автоматически при первом запуске:
```bash
docker compose up -d
```

### 2. Для production (Let's Encrypt)

#### Вариант A: Через certbot на хосте

```bash
# Установите certbot
apt-get install -y certbot

# Получите сертификат
certbot certonly --standalone -d your-domain.com

# Скопируйте сертификаты
mkdir -p ./nginx/ssl
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/ssl/key.pem

# Перезапустите
docker compose restart nginx
```

#### Вариант B: Обновите docker-compose.yml для монтирования

```yaml
nginx:
  volumes:
    - /etc/letsencrypt/live/your-domain.com:/etc/nginx/ssl:ro
```

### 3. Обновите .env
```env
WEBHOOK_URL=https://your-domain.com/webhook
WEBHOOK_PATH=/webhook
```

### 4. Перезапустите
```bash
docker compose restart
```

### 5. Проверка
```bash
# Проверка webhook
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo

# Health check
curl https://your-domain.com/health
```

## Полезные команды

```bash
# Логи
docker compose logs -f bot

# Перезапуск
docker compose restart bot

# Остановка
docker compose down

# Обновление (если используется Git)
git pull
docker compose up -d --build
```

## Проверка работы

```bash
# Health check
curl http://localhost:8000/health

# Статус webhook
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

