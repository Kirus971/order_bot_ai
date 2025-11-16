#!/bin/bash

# Скрипт для деплоя на удаленный сервер
# Использование: ./deploy.sh user@178.xxx.xxx.xxx /opt/order_bot

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка аргументов
if [ $# -lt 2 ]; then
    echo -e "${RED}Использование: $0 <user@host> <remote_path>${NC}"
    echo "Пример: $0 root@178.xxx.xxx.xxx /opt/order_bot"
    exit 1
fi

REMOTE_HOST=$1
REMOTE_PATH=$2

echo -e "${GREEN}Начинаем деплой на ${REMOTE_HOST}${NC}"

# Проверка подключения
echo -e "${YELLOW}Проверка подключения к серверу...${NC}"
ssh -o ConnectTimeout=5 $REMOTE_HOST "echo 'Подключение успешно'" || {
    echo -e "${RED}Не удалось подключиться к серверу${NC}"
    exit 1
}

# Создание архива
echo -e "${YELLOW}Создание архива проекта...${NC}"
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='Untitled.ipynb' \
    --exclude='*.log' \
    --exclude='venv' \
    --exclude='.venv' \
    -czf /tmp/order_bot_deploy.tar.gz .

# Копирование на сервер
echo -e "${YELLOW}Копирование файлов на сервер...${NC}"
scp /tmp/order_bot_deploy.tar.gz $REMOTE_HOST:/tmp/

# Распаковка на сервере
echo -e "${YELLOW}Распаковка файлов на сервере...${NC}"
ssh $REMOTE_HOST << EOF
    mkdir -p $REMOTE_PATH
    cd $REMOTE_PATH
    tar -xzf /tmp/order_bot_deploy.tar.gz
    rm /tmp/order_bot_deploy.tar.gz
    echo "Файлы распакованы"
EOF

# Проверка Docker
echo -e "${YELLOW}Проверка Docker...${NC}"
ssh $REMOTE_HOST "command -v docker >/dev/null 2>&1" && {
    echo -e "${GREEN}Docker найден, перезапуск контейнеров...${NC}"
    ssh $REMOTE_HOST << EOF
        cd $REMOTE_PATH
        docker compose down
        docker compose up -d --build
EOF
} || {
    echo -e "${YELLOW}Docker не найден, проверьте установку вручную${NC}"
}

# Очистка локального архива
rm /tmp/order_bot_deploy.tar.gz

echo -e "${GREEN}Деплой завершен!${NC}"
echo -e "${YELLOW}Не забудьте проверить .env файл на сервере${NC}"

