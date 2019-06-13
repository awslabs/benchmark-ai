#!/usr/bin/env bash

# Hack necessary to deploy image to a container running docker, without pushing it to a repo.
# Later solution can be a local repository service

CONTAINER=$1
IMAGE=$2

docker save ${IMAGE} | docker exec -i ${CONTAINER} docker load
