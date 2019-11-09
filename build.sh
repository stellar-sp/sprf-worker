#!/usr/bin/env bash

if [[ -z "$1" ]]
  then
    echo "No argument supplied, please pass 1 or 2 or ... for image tag"
    exit
fi


docker build . --no-cache --network=host -f Dockerfile-base-image -t smart-program/worker-base-image

docker build . --no-cache -f Dockerfile -t smart-program/sprf-worker:$1