# Order Bot — Telegram-бот для приёма заказов с искусственным интеллектом

Telegram-бот для автоматизации приёма и обработки заказов. Использует OpenAI для интеллектуального парсинга текстовых заказов, что позволяет клиентам удобно формировать заказы в свободной форме.

В качестве модели применяется **gpt-4o-mini** — она оптимально подходит для работы с текстом, обеспечивает высокую точность распознавания и при этом значительно экономичнее других современных аналогов.

Интеграция с **Google Таблицами** реализована по двум направлениям:
- **Ассортимент** загружается из таблицы, которую наполняют пользователи (с указанием наименований, цен и других характеристик)
- **Готовые заказы** автоматически записываются на отдельный лист для последующей обработки

Для получения данных ассортимента используется **Google Apps Script** — серверная логика на стороне Google Таблиц. Подробнее о работе со скриптами можно узнать в [официальной документации](https://developers.google.com/apps-script/guides/sheets?hl=ru).

## Архитектура

Проект построен разделен на следующие модули:

- **`src/bot/`** - Модуль Telegram бота (handlers, states, keyboards)
- **`src/ai_service/`** - Сервис обработки заказов через OpenAI
- **`src/database/`** - Модуль работы с базой данных (connection, models)
- **`src/config/`** - Конфигурация приложения
- **`src/utils/`** - Утилиты (форматирование сообщений)
- **`src/google_sheets/`** - Интеграция с Google Sheets
- **`nginx/`** - Nginx load balancer с фильтрацией IP адресов Telegram

- **`Mysql`** - Подразумевается, что Mysql уже развернута. Для интеграции с Гугл таблица лучше использовать MS sql, Mysql. Postgre sql не подойдет.

### Инфраструктура

```
┌─────────────┐
│   Telegram  │
│   Servers   │
└──────┬──────┘
       │ HTTPS (443)
       │ IP: 149.154.160.0/20, 91.108.4.0/22
       ▼
┌─────────────────┐
│  Nginx          │  ← Load Balancer
│  (Port 443)     │  ← IP Filtering
└────────┬────────┘
         │
         ├───► Bot 1 (Port 8000)
         ├───► Bot 2 (Port 8002) [будущее]
         └───► Bot N (Port 8001) [будущее]
```

**Особенности:**
- ✅ Балансировка нагрузки между ботами (least_conn алгоритм). На случай если будет несколько ботов.
- ✅ Фильтрация IP адресов - только официальные IP Telegram могут отправлять webhook
- ✅ SSL/TLS шифрование
- ✅ Автоматическая генерация самоподписанного сертификата для разработки
- ✅ Готовность к масштабированию (легко добавить больше ботов)

## Требования

- Python 3.11+
- MySQL база данных
- OpenAI API ключ
- Telegram Bot Token

## Установка и запуск

### 1. Клонирование и настройка

```bash
# Скопируйте .env.example в .env
cp .env.example .env

# Отредактируйте .env файл и укажите ваши настройки
nano .env
```

### 2. Запуск через Docker (рекомендуется)

```bash
# Сборка и запуск (включает Nginx load balancer)
docker compose up -d --build

# Просмотр логов всех сервисов
docker compose logs -f

# Просмотр логов конкретного сервиса
docker compose logs -f bot
docker compose logs -f nginx

# Остановка
docker compose down
```

**Примечание:** Nginx автоматически генерирует самоподписанный SSL сертификат при первом запуске. Для production используйте Let's Encrypt (см. [QUICK_DEPLOY.md](QUICK_DEPLOY.md)).

### 3. Запуск локально

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python -m src.main
```

## Настройка базы данных

Убедитесь, что в базе данных существуют необходимые таблицы. Вы можете использовать SQL скрипт из `database/init.sql`:

```bash
mysql -u your_user -p your_database < database/init.sql
```

Или создайте таблицы вручную:

### Таблица `users`
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    organization VARCHAR(255) NOT NULL,
    approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_approved (approved)
);
```

### Таблица `orders`
```sql
CREATE TABLE IF NOT EXISTS orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    order_data JSON NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);
```

### Таблица `assortment`
Таблица наполняется напрямую из гугл таблиц. На стороне GSH должен быть реализован функционал. (app script на JS)
```sql
CREATE TABLE assortment (
    good_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    price_c DECIMAL(10, 2),
    price_amt DECIMAL(10, 2),
    min_size DECIMAL(10, 2),
    PRIMARY KEY (good_id)
);
```

## Переменные окружения

Все настройки задаются через переменные окружения в файле `.env`:

### База данных
- `DB_HOST` - Хост базы данных
- `DB_PORT` - Порт базы данных
- `DB_NAME` - Имя базы данных
- `DB_USER` - Пользователь БД
- `DB_PASSWORD` - Пароль БД
- `DB_POOL_MIN` - Минимальный размер пула соединений (по умолчанию: 5)
- `DB_POOL_MAX` - Максимальный размер пула соединений (по умолчанию: 20)

### Telegram Bot
- `BOT_TOKEN` - Токен Telegram бота
- `BOT_ADMIN_IDS` - ID администраторов (через запятую)

### OpenAI
- `OPENAI_API_KEY` - API ключ OpenAI
- `OPENAI_MODEL` - Модель OpenAI (по умолчанию: gpt-4o-mini)
- `OPENAI_MAX_TOKENS` - Максимальное количество токенов (по умолчанию: 900)

### Google Sheets
- `GOOGLE_SHEETS_ID` - ID Google Таблицы (из URL)
- `GOOGLE_SHEETS_WORKSHEET` - Название листа (по умолчанию: "Заказы")
- `GOOGLE_SHEETS_CREDENTIALS_JSON` - JSON с учетными данными сервисного аккаунта (для Docker/cloud)
- `GOOGLE_SHEETS_CREDENTIALS_PATH` - Путь к файлу с учетными данными (для локальной разработки)

**Примечание:** Используйте либо `GOOGLE_SHEETS_CREDENTIALS_JSON`, либо `GOOGLE_SHEETS_CREDENTIALS_PATH`.

### Webhook (опционально)
- `WEBHOOK_URL` - Полный URL для webhook (например: https://your-domain.com/webhook)
- `WEBHOOK_PATH` - Путь для webhook endpoint (по умолчанию: /webhook)
- `WEBHOOK_CERTIFICATE_PATH` - Путь к SSL сертификату (опционально)

Если `WEBHOOK_URL` не указан, бот будет работать в режиме polling.

### Сервер
- `PORT` - Порт для FastAPI сервера (по умолчанию: 8000)

## Функциональность

1. **Регистрация пользователей**
   - Пользователь отправляет `/start`
   - Вводит название организации
   - Администратор подтверждает регистрацию

2. **Обработка заказов**
   - Пользователь отправляет заказ в свободной форме
   - AI парсит заказ и извлекает:
     - Товары и количество
     - Адрес доставки
     - Дату доставки
     - Тип оплаты
   - Пользователь подтверждает заказ
   - Заказ отправляется администратору
   - Администратор подтверждает заказ
   - **После подтверждения администратором заказ автоматически записывается в Google Таблицу и mysql**

## Структура проекта

```
.
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
└── src/
    ├── __init__.py
    ├── main.py
    ├── text.py
    ├── bot/
    │   ├── __init__.py
    │   ├── handlers.py
    │   ├── keyboards.py
    │   └── states.py
    ├── ai_service/
    │   ├── __init__.py
    │   └── order_parser.py
    ├── database/
    │   ├── __init__.py
    │   ├── connection.py
    │   └── models.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py
    ├── utils/
    │   ├── __init__.py
    │   └── formatters.py
    ├── google_sheets/
    │   ├── __init__.py
    │   └── service.py
    └── nginx/
        ├── Dockerfile
        ├── nginx.conf
        ├── generate-self-signed-cert.sh
        └── README.md
```

## Настройка Google Sheets

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API
3. Создайте сервисный аккаунт и скачайте JSON файл с ключами
4. Поделитесь Google Таблицей с email сервисного аккаунта (найдите email в JSON файле)
5. Скопируйте ID таблицы из URL (между `/d/` и `/edit`)
6. Укажите настройки в `.env` файле

## Режимы работы

### Polling (по умолчанию)
Если `WEBHOOK_URL` не указан, бот работает в режиме polling:
```bash
python -m src.main
```

### Webhook
Для production рекомендуется использовать webhook:
1. Укажите `WEBHOOK_URL` и `WEBHOOK_PATH` в `.env`
2. Убедитесь, что ваш сервер доступен по HTTPS
3. Запустите FastAPI сервер:
```bash
python -m src.main
# или через uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Деплой на сервер

Подробная инструкция по деплою на удаленный сервер находится в файле [DEPLOY.md](DEPLOY.md).

### Быстрый старт:

1. **На сервере** (первоначальная настройка):
   ```bash
   # Скопируйте setup_server.sh на сервер и запустите
   bash setup_server.sh
   ```

2. **С локальной машины** (деплой проекта):
   ```bash
   # Используйте скрипт деплоя
   ./deploy.sh root@178.xxx.xxx.xxx /opt/order_bot
   
   # Или вручную через Git
   ssh root@178.xxx.xxx.xxx
   cd /opt
   git clone <your-repo-url> order_bot
   cd order_bot
   # Создайте .env файл
   docker compose up -d --build
   ```

## Разработка

Для разработки рекомендуется использовать виртуальное окружение:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

## Логирование

Логи выводятся в консоль. Для Docker логи можно просмотреть через:

```bash
docker-compose logs -f bot
```


