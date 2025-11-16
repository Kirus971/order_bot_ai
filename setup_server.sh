#!/bin/bash

# Скрипт для первоначальной настройки сервера
# Запускать на удаленном сервере: bash setup_server.sh

set -e

echo "=== Настройка сервера для Order Bot ==="

# Обновление системы
echo "Обновление системы..."
apt-get update
apt-get upgrade -y

# Установка базовых пакетов
echo "Установка базовых пакетов..."
apt-get install -y \
    curl \
    wget \
    git \
    nano \
    htop \
    ufw

# Установка Docker
if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Добавление текущего пользователя в группу docker
    usermod -aG docker $USER
    
    # Установка Docker Compose
    apt-get install -y docker-compose-plugin
fi

# Установка Nginx (опционально, для webhook)
read -p "Установить Nginx для webhook? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Установка Nginx..."
    apt-get install -y nginx
    
    # Настройка firewall
    ufw allow 'Nginx Full'
    ufw allow 'OpenSSH'
    ufw --force enable
fi

# Создание директории для проекта
PROJECT_DIR="/opt/order_bot"
mkdir -p $PROJECT_DIR
echo "Директория создана: $PROJECT_DIR"

# Создание systemd service
echo "Создание systemd service..."
cat > /etc/systemd/system/order-bot.service << 'EOF'
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
EOF

systemctl daemon-reload

echo ""
echo "=== Настройка завершена ==="
echo ""
echo "Следующие шаги:"
echo "1. Скопируйте файлы проекта в $PROJECT_DIR"
echo "2. Создайте .env файл с настройками"
echo "3. Запустите: cd $PROJECT_DIR && docker compose up -d"
echo "4. Для автозапуска: systemctl enable order-bot.service"

