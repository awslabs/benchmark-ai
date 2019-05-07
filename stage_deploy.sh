#!/usr/bin/env bash

#Intermediate script to be used before we adopt kustomize

TARGET=$1

BASE_PATH=./deploy/base
TARGET_PATH=./deploy/${TARGET}

KUBE_ACTION=${2:-apply}

if [[ -d ${TARGET_PATH}/pre ]]; then
    kubectl apply --filename ${TARGET_PATH}/pre
fi

for yml in ${BASE_PATH}/*.yml; do
    echo "${KUBE_ACTION} ${yml}"

    basename_yml=$(basename ${yml})

    overlay="${TARGET_PATH}/overlay/${basename_yml}"
    override="${TARGET_PATH}/${basename_yml}"

    echo $overlay

    if [[ -f ${overlay} ]]; then
        echo "Overlay found: ${overlay}"
        kubectl patch --patch="$(cat ${overlay})" --filename="${yml}" --local --output yaml --type merge | kubectl ${KUBE_ACTION} -f -
    elif [[ -f ${override} ]]; then
        kubectl ${KUBE_ACTION} -f "${override}"
    else
        kubectl ${KUBE_ACTION} -f "${yml}"
    fi
done
