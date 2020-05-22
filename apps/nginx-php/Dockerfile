FROM alpine:3.11

# Install nginx & gettext (envsubst)
# Create cachedir and fix permissions
RUN apk add --no-cache \
    supervisor \
    nginx \
    php7 \
    php7-fpm \
    curl

COPY ./supervisord.conf /etc/supervisord.conf
COPY ./php-fpm-www.conf /etc/php7/php-fpm.d/www.conf
COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./index1.php /var/www/html/index1.php

RUN set -x \
    && mkdir -pv /var/www/html /var/cache/nginx /var/log/nginx /var/lib/nginx /var/tmp/nginx \
    && chown -R nginx:nginx /var/www /var/cache/nginx /var/lib/nginx /var/tmp/nginx \
    && chmod -R 777 /var/www /var/cache/nginx /var/lib/nginx /var/tmp/nginx \
    && chmod -R 777 /etc /var/www /run /var/run /var/cache /var/log

# Nginx on :8080
EXPOSE 8080

WORKDIR /var/www/html

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
