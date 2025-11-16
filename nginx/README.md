# Nginx Load Balancer для Order Bot

Nginx конфигурация для балансировки нагрузки между несколькими экземплярами ботов.

## Особенности

- ✅ Балансировка нагрузки между ботами (least_conn алгоритм)
- ✅ Фильтрация IP адресов Telegram (только разрешенные IP могут отправлять webhook)
- ✅ SSL/TLS поддержка
- ✅ Автоматическая генерация самоподписанного сертификата для разработки
- ✅ Поддержка Let's Encrypt для production

## Структура

```
nginx/
├── Dockerfile              # Docker образ для Nginx
├── nginx.conf              # Основная конфигурация Nginx
├── generate-self-signed-cert.sh  # Скрипт генерации сертификата
└── README.md               # Этот файл
```

## IP адреса Telegram

Nginx настроен на прием запросов только с официальных IP адресов Telegram:
- `149.154.160.0/20`
- `91.108.4.0/22`

Все остальные IP адреса блокируются для `/webhook` endpoint.

## Добавление новых ботов

Для добавления нового бота в балансировку:

1. Добавьте новый сервис в `docker-compose.yml`:
```yaml
bot2:
  build: .
  container_name: order_bot_2
  # ... остальные настройки
```

2. Обновите `nginx/nginx.conf`:
```nginx
upstream bot_backend {
    least_conn;
    server bot:8000 max_fails=3 fail_timeout=30s;
    server bot2:8000 max_fails=3 fail_timeout=30s;  # Новый бот
}
```

3. Перезапустите:
```bash
docker compose up -d --build
```

## SSL сертификаты

### Для разработки (самоподписанный)

Сертификат генерируется автоматически при первом запуске контейнера.

### Для production (Let's Encrypt)

1. Установите certbot на хосте:
```bash
apt-get install certbot
```

2. Получите сертификат:
```bash
certbot certonly --webroot -w ./nginx/certbot -d your-domain.com
```

3. Скопируйте сертификаты:
```bash
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/ssl/key.pem
```

4. Обновите docker-compose.yml для монтирования сертификатов:
```yaml
volumes:
  - /etc/letsencrypt/live/your-domain.com:/etc/nginx/ssl:ro
```

5. Настройте автообновление сертификата через cron или systemd timer.

## Мониторинг

### Логи Nginx

```bash
# Все логи
docker compose logs nginx

# Только ошибки
docker compose exec nginx tail -f /var/log/nginx/error.log

# Только доступ
docker compose exec nginx tail -f /var/log/nginx/access.log
```

### Проверка балансировки

```bash
# Проверка upstream статуса
docker compose exec nginx nginx -t

# Проверка подключений
docker compose exec nginx netstat -an | grep 8000
```

## Алгоритмы балансировки

Текущий алгоритм: `least_conn` - распределение по наименьшему количеству соединений.

Другие доступные алгоритмы:
- `round_robin` - по кругу (по умолчанию)
- `ip_hash` - по IP адресу клиента
- `least_conn` - по наименьшему количеству соединений
- `weight=X` - с весами для каждого сервера

Пример с весами:
```nginx
upstream bot_backend {
    server bot:8000 weight=3;
    server bot2:8000 weight=2;
    server bot3:8000 weight=1;
}
```

## Безопасность

1. **IP фильтрация**: Только IP адреса Telegram могут отправлять webhook
2. **SSL/TLS**: Все соединения зашифрованы
3. **Rate limiting**: Можно добавить ограничение запросов (см. ниже)

### Добавление Rate Limiting

Добавьте в `nginx.conf` в секцию `http`:

```nginx
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=10r/s;

server {
    ...
    location /webhook {
        limit_req zone=webhook_limit burst=20 nodelay;
        # ... остальная конфигурация
    }
}
```

## Troubleshooting

### Nginx не запускается

```bash
# Проверьте конфигурацию
docker compose exec nginx nginx -t

# Проверьте логи
docker compose logs nginx
```

### Сертификат не работает

```bash
# Проверьте наличие сертификата
docker compose exec nginx ls -la /etc/nginx/ssl/

# Проверьте права доступа
docker compose exec nginx cat /etc/nginx/ssl/cert.pem
```

### Боты не доступны через Nginx

```bash
# Проверьте сеть
docker compose exec nginx ping bot

# Проверьте порты
docker compose exec nginx netstat -tuln | grep 8000
```

