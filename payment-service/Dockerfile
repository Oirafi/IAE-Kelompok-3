FROM php:8.2-cli-alpine

WORKDIR /app

RUN apk add --no-cache libzip-dev zip unzip
RUN docker-php-ext-install pdo pdo_mysql

COPY . .

EXPOSE 3005
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=3005"]