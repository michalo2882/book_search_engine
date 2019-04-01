#!/bin/bash

uwsgi --chdir=/app \
    --module=book_search.wsgi:application \
    --env DJANGO_SETTINGS_MODULE=book_search.settings \
    --master \
    --pidfile=/tmp/app-uwsgi.pid \
    --socket=0.0.0.0:49152 \
    --processes=4 \
    --harakiri=20 \
    --max-requests=5000 \
    --buffer-size=16384 \
    --vacuum &

/usr/bin/memcached -m 64 -p 11211 -u memcache -l 127.0.0.1 &
nginx -g "daemon off;"
