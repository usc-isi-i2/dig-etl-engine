#!/usr/bin/env bash

opt="${1}"

source ./VERSION

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
