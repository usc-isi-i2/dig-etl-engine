#!/usr/bin/env bash

# usage:
# ./engine.sh up
# ./start.sh +dev up
# ./engine.sh +dev +ache up -d
# ./engine.sh config
# ./engine.sh stop
# ./engine.sh down
# ./engine.sh restart mydig_ws

cmd="-f docker-compose.yml"
yml="" # additional yml files
operation_up=false

# find out if it is operation up
for arg in $@; do
    if [ "${arg}" == "up" ]; then
        operation_up=true
        echo "" > .engine.status
    fi
done

if [ "$operation_up" == true ]; then
    # add parameter from env file
    source ./.env
    for arg in $(echo $DIG_ADD_ONS | tr "," "\n"); do
        cmd="$cmd -f docker-compose.${arg}.yml"
        yml="$yml -f docker-compose.${arg}.yml"
    done
else
    # add parameter from .engine.status
    cmd="$cmd $(head -n 1 .engine.status)"
fi

# add parameter from command line
for arg in $@; do
    if [[ "${arg:0:1}" == "+" ]]; then
        arg=${arg:1} # remove plus sign
        cmd="$cmd -f docker-compose.${arg}.yml"
        yml="$yml -f docker-compose.${arg}.yml"
    else
        cmd="$cmd ${arg}"
    fi
done

if [ "$operation_up" == true ]; then
    echo "$yml" > .engine.status
fi

cmd="docker-compose $cmd"
#echo $cmd
eval $cmd
