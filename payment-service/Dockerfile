FROM php:8.2.19-cli

WORKDIR /app

RUN apt-get update && apt-get install -y libzip-dev zip unzip
RUN docker-php-ext-install pdo pdo_mysql

COPY . .

EXPOSE 3005
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=3005"]