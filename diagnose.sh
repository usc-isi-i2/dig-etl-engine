#!/usr/bin/env bash

echo "=================================================="
echo "             myDIG Diagnostic Tool"
echo "--------------------------------------------------"

echo "File system information:"
df -h
echo "--------------------------------------------------"

echo "CPU and Memory information:"
if [[ "$OSTYPE" == "linux-gnu" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
    top -n 1 | head -n 5
elif [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "freebsd"* ]]; then
    top -l 1 | head -n 10 # only for mac
elif [[ "$OSTYPE" == "win32" ]]; then
    echo "Doesn't support win32 command prompt, please run in Cygwin."
else
    echo "Unknown system."
fi
echo "--------------------------------------------------"

source ./.env
CONTAINER_MYDIG_WS="${COMPOSE_PROJECT_NAME}_mydig_ws_1"
CONTAINER_ETL_ENGINE="${COMPOSE_PROJECT_NAME}_dig_etl_engine_1"
CONTAINER_NGINX="${COMPOSE_PROJECT_NAME}_nginx_1"
CONTAINER_ELASTICSEARCH="${COMPOSE_PROJECT_NAME}_elasticsearch_1"
CONTAINER_LOGSTASH="${COMPOSE_PROJECT_NAME}_logstash_1"
CONTAINER_KIBANA="${COMPOSE_PROJECT_NAME}_kibana_1"
CONTAINER_SANDPAPER="${COMPOSE_PROJECT_NAME}_sandpaper_1"
CONTAINER_KAFKA="${COMPOSE_PROJECT_NAME}_kafka_1"
CONTAINER_ZOOKEEPER="${COMPOSE_PROJECT_NAME}_zookeeper_1"
CONTAINER_KAFKA_MANAGER="${COMPOSE_PROJECT_NAME}_kafka_manager_1"
CONTAINER_LANDMARK_MYSQL="${COMPOSE_PROJECT_NAME}_landmark-mysql_1"
CONTAINER_LANDMARK_PORTAL="${COMPOSE_PROJECT_NAME}_landmark-portal_1"
CONTAINER_LANDMARK_REST="${COMPOSE_PROJECT_NAME}_landmark-rest_1"
CONTAINER_DIGUI="${COMPOSE_PROJECT_NAME}_digui_1"
# use mydig_ws container as test container for inner network
TEST_CONTAINER_NAME=${CONTAINER_MYDIG_WS}

echo "[Core Containers]"
echo "--------------------------------------------------"

echo "Diagnose mydig_ws:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_MYDIG_WS}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
    echo "All the rest of the tests are based on mydig_ws, aborted!"
    exit
else
    echo "[done]"

    # webservice
    echo -n "Checking myDIG backend ... "
    resp=$(docker exec -it ${TEST_CONTAINER_NAME} /bin/sh -c \
        "curl -s -o /dev/null -I -w \"%{http_code}\" http://mydig_ws:9879")
    if [ "$resp" == "200" ]; then
        echo "[done]"
    else
        echo "[ERROR]"
    fi
    # frontend
    echo -n "Checking myDIG frontend ... "
    resp=$(docker exec -it ${TEST_CONTAINER_NAME} /bin/sh -c \
        "curl -s -o /dev/null -I -w \"%{http_code}\" http://mydig_ws:9880")
    if [ "$resp" == "200" ]; then
        echo "[done]"
    else
        echo "[ERROR]"
    fi
    # spacy daemon
    echo -n "Checking spaCy Daemon ... "
    resp=$(docker exec -it ${TEST_CONTAINER_NAME} /bin/sh -c \
        "curl -s -o /dev/null -I -w \"%{http_code}\" http://localhost:12121")
    if [ "$resp" == "200" ]; then
        echo "[done]"
    else
        echo "[ERROR]"
    fi
    # spacy ui
    echo -n "Checking spaCy UI ... "
    resp=$(docker exec -it ${TEST_CONTAINER_NAME} /bin/sh -c \
        "curl -s -o /dev/null -I -w \"%{http_code}\" http://mydig_ws:9881")
    if [ "$resp" == "200" ]; then
        echo "[done]"
    else
        echo "[ERROR]"
    fi

fi
echo "--------------------------------------------------"


echo "Diagnose dig-etl-engine:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_ETL_ENGINE}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
    # etl webservice
    echo -n "Checking ETL web service ... "
    resp=$(docker exec -it ${TEST_CONTAINER_NAME} /bin/sh -c \
        "curl -s -o /dev/null -I -w \"%{http_code}\" http://dig_etl_engine:9999")
    if [ "$resp" == "200" ]; then
        echo "[done]"
    else
        echo "[ERROR]"
    fi
fi
echo "--------------------------------------------------"


echo "Diagnose zookeeper:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_ZOOKEEPER}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"


echo "Diagnose kafka:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_KAFKA}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"


echo "Diagnose kibana:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_KIBANA}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"


echo "Diagnose sandpaper:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_SANDPAPER}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"


echo "Diagnose logstash:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_LOGSTASH}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"


echo "Diagnose elasticsearch:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_ELASTICSEARCH}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"

echo "Diagnose landmark-mysql:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_LANDMARK_MYSQL}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"

echo "Diagnose landmark-portal:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_LANDMARK_PORTAL}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"

echo "Diagnose landmark-rest:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_LANDMARK_REST}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"

echo "Diagnose digui:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_DIGUI}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"


echo "[Add-on Containers]"
echo "--------------------------------------------------"

echo "Diagnose kafka_manager:"
echo -n "Checking container ... "
container_id=$(docker ps -q --filter "name=${CONTAINER_KAFKA_MANAGER}")
if [ -z ${container_id} ]; then
    echo "[ERROR]"
else
    echo "[done]"
fi
echo "--------------------------------------------------"
