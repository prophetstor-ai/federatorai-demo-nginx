FROM richarvey/nginx-php-fpm

## define SKIP_CHOWN to avoid error "chown: /var/www/html: Operation not permitted" in OpenShift deployment
ENV SKIP_CHOWN 1

COPY index1.php /var/www/html/

RUN set -x \
    ## Avoid "No such file or directory" error
    && touch /etc/TZ \
    ## Avoid "Error: Can't drop privilege as nonroot user" error in OpenShift deployment
    && sed -i -e '/user=/d' /etc/supervisord.conf \
    ## Avoid "failed to chown() the socket '/var/run/php-fpm.sock': Operation not permitted" error in OpenShift deployment
    && sed -i -e "/listen.owner/d" /usr/local/etc/php-fpm.d/www.conf \
    ## Need to bind port>1023 in OpenShift deployment
    && sed -i -e '/ipv6only=on/d' -e 's/listen.*.80/listen 8080/g' -e 's/listen.*.443/listen 8443/g' /etc/nginx/sites-available/* \
    ## Avoid "Permission denied" error in OpenShift deployment
    && chmod -R 777 /root /usr/local /etc /var/www /var/run /var/cache
