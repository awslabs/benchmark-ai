#!/usr/bin/env bash

TIMEOUT=${2:-300}
JOB_NAME=$1
END=$(($SECONDS+$TIMEOUT))

kubectl="kubectl ${KUBECTL_FLAGS}"

_get_status(){
    local JOB_NAME=$1
    local STATUS=$2

    $kubectl get jobs $JOB_NAME -o jsonpath="{.status.conditions[?(@.type==\"${STATUS}\")].status}"
}

_dump_log(){
    local JOB_NAME=$1
    local POD_NAME=$($kubectl ${KUBECTL_FLAGS} get pod  -l job-name=$JOB_NAME -o=jsonpath='{range .items[*]}{.metadata.name}')
    $kubectl logs ${POD_NAME}
}

until [[ $SECONDS -gt $END ]] || \
    [[ $(_get_status $JOB_NAME "Failed") == "True" ]] || \
    [[ $(_get_status $JOB_NAME "Complete")  == "True"  ]]; do
    echo "Still waiting..."
    sleep 1s
done
echo "Job finished"

[[ $(_get_status $JOB_NAME "Failed") == "True" ]] && _dump_log $JOB_NAME &&exit 1
[[ $(_get_status $JOB_NAME "Complete")  == "True"  ]] && _dump_log $JOB_NAME && exit 0
echo "Timeout" && exit 2


