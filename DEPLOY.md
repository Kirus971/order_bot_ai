# Инструкция по деплою на удаленный сервер

## Предварительные требования

На сервере должны быть установлены:
- Git
- Docker и Docker Compose (рекомендуется)
- Или Python 3.11+ (если без Docker)

**Примечание**: Nginx теперь включен в Docker Compose и не требует отдельной установки на хосте.

## Вариант 1: Деплой через Docker (рекомендуется)

### 1. Подключение к серверу

```bash
ssh root@178.xxx.xxx.xxx
# или
ssh user@178.xxx.xxx.xxx
```

### 2. Клонирование проекта

```bash
# Перейдите в нужную директорию
cd /opt  # или /var/www, или другую по вашему выбору

# Клонируйте репозиторий (если есть Git репозиторий)
git clone <your-repo-url> order_bot
cd order_bot

# Или создайте директорию и скопируйте файлы
mkdir -p /opt/order_bot
# Затем скопируйте все файлы проекта через scp или rsync
```

### 3. Копирование файлов через SCP (если нет Git репозитория)

С локального компьютера:

```bash
# Создайте архив проекта (исключая ненужные файлы)
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='Untitled.ipynb' \
    -czf order_bot.tar.gz .

# Скопируйте на сервер
scp order_bot.tar.gz root@178.xxx.xxx.xxx:/opt/

# На сервере распакуйте
ssh root@178.xxx.xxx.xxx
cd /opt
tar -xzf order_bot.tar.gz -C order_bot
cd order_bot
```

### 4. Создание .env файла

```bash
# На сервере создайте .env файл
nano .env
```

Заполните следующий контент:

```env
# Database Configuration
DB_HOST=178.***.***.***
DB_PORT=3306
DB_NAME=order_bot
DB_USER=telegram_bot
DB_PASSWORD=your_actual_password
DB_POOL_MIN=5
DB_POOL_MAX=20

# Bot Configuration
BOT_TOKEN=your_telegram_bot_token
BOT_ADMIN_IDS=your_admins_ids

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini # or choise your model
OPENAI_MAX_TOKENS=900

# Google Sheets Configuration
GOOGLE_SHEETS_ID=your_google_sheets_id
GOOGLE_SHEETS_WORKSHEET=Заказы
# Используйте JSON строку для Docker
GOOGLE_SHEETS_CREDENTIALS_JSON={"type": "service_account", "project_id": "...", ...}

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com/webhook
WEBHOOK_PATH=/webhook
# WEBHOOK_CERTIFICATE_PATH=/path/to/public.pem  # Опционально

# Server Configuration
PORT=8000
```

Сохраните файл (Ctrl+O, Enter, Ctrl+X в nano).

### 5. Установка Docker (если не установлен)

```bash
# Для Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установка Docker Compose
apt-get update
apt-get install docker-compose-plugin

# Проверка
docker --version
docker compose version
```

### 6. Запуск через Docker Compose

```bash
# Сборка и запуск
docker compose up -d --build

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down

# Перезапуск
docker compose restart
```

### 7. Настройка автозапуска (systemd)

Создайте systemd service для автозапуска:

```bash
sudo nano /etc/systemd/system/order-bot.service
```

Содержимое:

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
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активируйте сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable order-bot.service
sudo systemctl start order-bot.service

# Проверка статуса
sudo systemctl status order-bot.service
```

## Вариант 2: Деплой без Docker (напрямую)

### 1-3. Те же шаги что и выше

### 4. Установка Python и зависимостей

```bash
# Обновление системы
apt-get update
apt-get upgrade -y

# Установка Python 3.11 и зависимостей
apt-get install -y python3.11 python3.11-venv python3-pip
apt-get install -y default-libmysqlclient-dev pkg-config gcc

# Создание виртуального окружения
cd /opt/order_bot
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Создание systemd service

```bash
sudo nano /etc/systemd/system/order-bot.service
```

Содержимое:

```ini
[Unit]
Description=Order Bot Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/order_bot
Environment="PATH=/opt/order_bot/venv/bin"
ExecStart=/opt/order_bot/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активируйте:

```bash
sudo systemctl daemon-reload
sudo systemctl enable order-bot.service
sudo systemctl start order-bot.service

# Проверка
sudo systemctl status order-bot.service
sudo journalctl -u order-bot.service -f
```

## Настройка Nginx для Webhook (если не использовать докер)

### 1. Установка Nginx

```bash
apt-get install -y nginx
```

### 2. Настройка SSL сертификата (Let's Encrypt)

```bash
# Установка Certbot
apt-get install -y certbot python3-certbot-nginx

# Получение сертификата
certbot --nginx -d your-domain.com

# Автообновление
certbot renew --dry-run
```

### 3. Настройка Nginx конфигурации

```bash
sudo nano /etc/nginx/sites-available/order-bot
```

Пример содержимого:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /webhook {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/order-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Проверка работы

### Проверка логов

```bash
# Docker
docker compose logs -f bot

# Systemd
sudo journalctl -u order-bot.service -f

# Прямой запуск
tail -f /opt/order_bot/logs/app.log
```

### Проверка endpoints

```bash
# Health check
curl http://localhost:8000/health

# Статус
curl http://localhost:8000/
```

### Проверка webhook

```bash
# Проверка установленного webhook
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

## Обновление проекта

### Если используется Git:

```bash
cd /opt/order_bot
git pull origin main
docker compose restart  # или systemctl restart order-bot
```

### Если файлы копируются вручную:

```bash
# На локальной машине
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' -czf order_bot.tar.gz .

# Копирование на сервер
scp order_bot.tar.gz root@178.xxx.xxx.xxx:/opt/

# На сервере
cd /opt/order_bot
docker compose down
cd /opt
tar -xzf order_bot.tar.gz -C order_bot
cd order_bot
docker compose up -d --build
```

## Полезные команды

```bash
# Просмотр запущенных контейнеров
docker ps

# Вход в контейнер
docker compose exec bot bash

# Перезапуск бота
docker compose restart bot

# Просмотр использования ресурсов
docker stats

# Очистка неиспользуемых образов
docker system prune -a
```

## Устранение проблем

### Бот не запускается

1. Проверьте логи: `docker compose logs bot` или `journalctl -u order-bot`
2. Проверьте .env файл на наличие всех необходимых переменных
3. Проверьте подключение к базе данных
4. Проверьте токен бота

### Webhook не работает

1. Проверьте, что сервер доступен по HTTPS
2. Проверьте настройки Nginx
3. Проверьте логи: `tail -f /var/log/nginx/error.log`
4. Проверьте webhook через API: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Проблемы с Google Sheets

1. Проверьте правильность JSON с учетными данными
2. Убедитесь, что таблица расшарена с email сервисного аккаунта
3. Проверьте ID таблицы в .env
4. Проверьте логи на наличие ошибок

## Безопасность

1. **Не коммитьте .env файл в Git**
2. **Используйте сильные пароли для БД**
3. **Ограничьте доступ к серверу через firewall:**
   ```bash
   ufw allow 22/tcp    # SSH
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw enable
   ```
4. **Регулярно обновляйте систему:**
   ```bash
   apt-get update && apt-get upgrade -y
   ```

