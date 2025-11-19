# FROM nginx:alpine

# # Копируем конфигурацию
# COPY nginx.conf /etc/nginx/nginx.conf

# # Создаем директорию для SSL сертификатов
# RUN mkdir -p /etc/nginx/ssl

# # Создаем директорию для certbot
# RUN mkdir -p /var/www/certbot

# # Expose порты
# EXPOSE 80 443

# # Запуск Nginx
# CMD ["nginx", "-g", "daemon off;"]

FROM nginx:alpine

# Копируем конфигурацию
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем директории
RUN mkdir -p /etc/nginx/ssl /var/log/nginx /var/www/certbot

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]