#!/usr/bin/env bash

# usage:
# ./start.sh up
# ./start.sh +dev up
# ./start.sh +dev +ache up -d
# ./start.sh +dev config
# ./start.sh +dev down
# ./start.sh +dev restart mydig_ws

cmd="docker-compose -f docker-compose.yml"

for arg in $@; do
    if [[ "${arg:0:1}" == "+" ]]; then
        arg=${arg:1} # remove plus sign
        cmd="$cmd -f docker-compose.${arg}.yml"
    else
        cmd="$cmd ${arg}"
    fi
done

#echo $cmd
eval $cmd
