#!/bin/sh

# Генерация самоподписанного SSL сертификата для разработки
# Для production используйте Let's Encrypt

if [ ! -f /etc/nginx/ssl/cert.pem ] || [ ! -f /etc/nginx/ssl/key.pem ]; then
    echo "Генерация самоподписанного SSL сертификата..."
    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem \
        -subj "/C=RU/ST=State/L=City/O=Organization/CN=localhost"
    echo "Сертификат создан!"
else
    echo "Сертификат уже существует"
fi

