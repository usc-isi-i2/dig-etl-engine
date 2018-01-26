#!/usr/bin/env bash

name="${1}"
opt="${2}"

source ./VERSION

if [ "${name}" == "etk" ]; then
    if [ "${opt}" == "build" ]; then
        echo "building ETK image..."
        docker build --build-arg ETK_VERSION=${ETK_VERSION} -t uscisii2/etk:${ETK_VERSION} -f Dockerfile-etk .
    elif [ "$opt" == "push" ]; then
        echo "pushing ETK image..."
        docker push uscisii2/etk:${ETK_VERSION}
    fi
elif [ "${name}" == "engine" ]; then
    if [ "${opt}" == "build" ]; then
        echo "building DIG ETL Engine image..."
        docker build --build-arg ETK_VERSION=${ETK_VERSION} -t uscisii2/dig-etl-engine:${DIG_ETL_ENGINE_VERSION} .
    elif [ "$opt" == "push" ]; then
        echo "pushing DIG ETL Engine image..."
        docker push uscisii2/dig-etl-engine:${DIG_ETL_ENGINE_VERSION}
    elif [ "$opt" == "tag" ]; then
        echo "tagging DIG ETL Engine..."
        git tag ${DIG_ETL_ENGINE_VERSION}
    fi
fi