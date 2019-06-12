#!/usr/bin/env bash
CONTAINER=$1
IMAGE=$2

docker save ${IMAGE} | docker exec -i $CONTAINER docker load