#!/usr/bin/env bash

name=${1}

source ./VERSION

if [ "${1}" == "etk" ]; then
    echo "building ETK base image..."
    docker build --build-arg ETK_VERSION=${ETK_VERSION} -t uscisii2/etk:${ETK_VERSION} -f Dockerfile-etk .
elif [ "${1}" == "engine" ]; then
    echo "building DIG ETL Engine image..."
    docker build --build-arg ETK_VERSION=${ETK_VERSION} -t uscisii2/dig-etl-engine:${DIG_ETL_ENGINE_VERSION} .
fi
