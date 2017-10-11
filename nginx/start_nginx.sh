#!/usr/bin/env bash

DIG_AUTH_USER="${DIG_AUTH_USER:-admin}"
DIG_AUTH_PASSWORD="${DIG_AUTH_PASSWORD:-123}"
DIG_AUTH_ENABLE="${DIG_AUTH_ENABLE-true}"

if [ -z "${DIG_AUTH_USER}" ]; then
    DIG_AUTH_USER=admin
fi
if [ -z "${DIG_AUTH_PASSWORD}" ]; then
    DIG_AUTH_PASSWORD=123
fi
if [ -z "${DIG_AUTH_ENABLE}" ]; then
    DIG_AUTH_ENABLE=true
fi

if [ "${DIG_AUTH_ENABLE}" = "true" ]; then
    echo ${DIG_AUTH_USER}:$(openssl passwd -apr1 ${DIG_AUTH_PASSWORD}) > /etc/nginx/.htpasswd
fi

nginx -g "daemon off;"