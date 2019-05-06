#!/usr/bin/env bash

TARGET=$1

BASE_PATH=./deploy/base
TARGET_PATH=./deploy/${TARGET}

if [[ -d ${TARGET_PATH}/pre ]]; then
    kubectl apply --filename ${TARGET_PATH}/pre
fi

for yml in ${BASE_PATH}/*.yml; do
    echo "Applying ${yml}"

    potential_overlay="${TARGET_PATH}/overlay/$(basename ${yml})"

    echo $potential_overlay

    if [[ -f ${potential_overlay} ]]; then
        echo "Overlay found: ${potential_overlay}"

        kubectl patch --patch="$(cat $potential_overlay)" --filename=$yml --local --output yaml --type merge | kubectl apply -f -
    else
        kubectl apply -f $yml
    fi

done
