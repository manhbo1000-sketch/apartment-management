FROM nginxinc/nginx-unprivileged:1.31-alpine3.24

USER root
RUN rm -f /var/log/nginx/access.log /var/log/nginx/error.log \
    && mkdir -p /var/log/nginx \
    && chown 101:2000 /var/log/nginx \
    && chmod 0750 /var/log/nginx
COPY --chown=101:2000 default.conf /etc/nginx/conf.d/default.conf
USER 101:2000
