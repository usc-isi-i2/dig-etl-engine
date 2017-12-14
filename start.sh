#!/usr/bin/env bash

cmd="docker-compose -f docker-compose.yml"
cmd_suffix="up"

for arg in $@; do
    if [ "$arg" == "-d" ]; then
        cmd_suffix="up -d"
    elif [ "$arg" == "config" ]; then
        cmd_suffix="config"
    else
        cmd="$cmd -f docker-compose.${arg}.yml"
    fi
done

cmd="$cmd $cmd_suffix"
#echo $cmd
eval $cmd
