#!/bin/bash

print_unsupported_verb() {
    local object=$1
    local verb=$2
    printf "Unsupported verb ${verb} for object ${object}\n"
}

_create_configmap_yaml_from_terraform_outputs() {
    local outputs=$(terraform output -json)
    local configmap_data=""
    for row in $(echo "${outputs}" | jq -r 'to_entries | .[] | @base64'); do
        # Use base64 because the output might contain a \n, which will break this whole loop
        _jq() {
            echo ${row} | base64 --decode | jq -r ${1}
        }

        key=$(_jq '.key')
        value=$(_jq '.value.value')
        sensitive=$(_jq '.value.sensitive')
        # Avoid sensitive and values with newlines
        if [[ ($sensitive == "false") && ("$value" != *$'\n'*) ]]; then
            configmap_data="$configmap_data\n  $key: $value"
        fi
    done

    # printf => To interpret the \n symbols in the variable
    # tail => To skip the first line, which should be empty
    configmap_data=$(printf "$configmap_data" | tail -n +2)

cat << EOF
apiVersion: v1
data:
$configmap_data
kind: ConfigMap
metadata:
  name: outputs-infrastructure
EOF
}

create_infra() {
    local cluster_name=""
    local region=""
    local prefix_list_id=""
    local validate=true

    for arg in "$@"; do
        case "${arg}" in
        --name=*)
            cluster_name="${arg#*=}"
            ;;
        --aws-region=*)
            region="${arg#*=}"
            ;;
        --aws-prefix-list-id=*)
            prefix_list_id="${arg#*=}"
            ;;
        --no-validate)
            validate=false
            ;;
        esac
    done

    #Temporary behavior
    [ -z "$prefix_list_id" ] && printf "Missing required argument --aws-prefix-list-id\n" && return 1

    cd $data_dir

    local vars=""

    [ -n "$cluster_name" ] && vars="${vars} -var cluster_name=${cluster_name}"
    [ -n "$region" ] && vars="${vars} -var region=${region}"
    [ -n "$prefix_list_id" ] && vars="${vars} -var prefix_list_ids=[\"${prefix_list_id}\"]"

    terraform init $terraform_dir
    terraform get $terraform_dir

    terraform plan --state=$terraform_state --out=$terraform_plan ${vars} $terraform_dir
    terraform apply $terraform_plan
    terraform output kubectl_config >kubeconfig

    #Make private key not public accessible
    local bastion_pem_filename=$(terraform output bastion_pem_filename)
    chmod 400 $bastion_pem_filename

    $kubectl apply -f fluentd-daemonset.yaml
    $kubectl apply -f autoscaler-deployment.yaml

    $kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v1.11/nvidia-device-plugin.yml
    $kubectl apply -f $project_dir/metrics-pusher/metrics-pusher-roles.yaml

    _create_configmap_yaml_from_terraform_outputs | $kubectl apply -f -

    _install_kubeflow_mpi_operator

    [ "$validate" == false ] || validate_infra $@
}

_install_kubeflow_mpi_operator() {
    if [ ! -d "kubeflow-mpi" ]; then
        mkdir kubeflow-mpi
        cd kubeflow-mpi
        git init
        git remote add origin -f https://github.com/kubeflow/mpi-operator.git
        git config --local core.sparsecheckout true
        echo "deploy/*" >>.git/info/sparse-checkout
        git pull --depth=1 origin master
        cd ..
    fi
    $kubectl apply -f kubeflow-mpi/deploy/
}
destroy_infra() {
    cd $data_dir

    terraform destroy --state=$terraform_state -auto-approve $terraform_dir
}

get_infra() {
    for arg in "$@"; do
        printf "\n----------\n"
        case "${arg}" in
        --nodes)
            $kubectl get nodes -o wide
            ;;
        --aws-es)
            terraform output --state=$terraform_state es_endpoint
            ;;
        --aws-cluster)
            terraform output --state=$terraform_state region
            terraform output --state=$terraform_state cluster_name
            terraform output --state=$terraform_state cluster_endpoint
            ;;
        --aws-bastion-ip)
            terraform output --state=$terraform_state bastion_public_ip
            ;;
        esac
    done
    printf "\n----------\n"
}

__validate_mpi_job(){
    printf "MPI Job is present"
    local kind=$($kubectl get crd mpijobs.kubeflow.org --output=json 2>/dev/null | jq .kind --raw-output)
    [ "$kind" == "CustomResourceDefinition" ] || return 1
}

validate_infra(){
    local all_ok=true
    for rule in __validate_mpi_job; do
        local result=true
        eval $rule || result=false

        printf "..."

        [ "$result" == false ] && printf "FAILED\n" && all_ok=false || printf "PASSED\n"  
    done
    [ "$all_ok" == true ] || return 1
}

get_benchmark() {
    local benchmark_name=""

    for arg in "$@"; do
        case "${arg}" in
        --name=*)
            benchmark_name="${arg#*=}"
            ;;
        esac
    done

    [ -z "$benchmark_name" ] && printf "Missing required argument --name\n" && return 1

    local bastion_pem_filename=$(terraform output --state=$terraform_state bastion_pem_filename)
    local bastion_ip=$(terraform output --state=$terraform_state bastion_public_ip)
    local es_endpoint=$(terraform output --state=$terraform_state es_endpoint)

    local query_body="{\"from\" : 0, \"size\" : 1000,\"query\" : {\"term\" : { \"kubernetes.labels.job-name\":\"${benchmark_name}\" }}}"

    local curl_cmd="curl -X POST -s -H 'Content-Type: application/json' -d '$query_body' ${es_endpoint}/_search"

    ssh -q -o StrictHostKeyChecking=no -i $data_dir/$bastion_pem_filename ubuntu@$bastion_ip "${curl_cmd}" | jq '.hits.hits[]._source | "(\(."@timestamp") \(.log)"' -j | sort
}

run_benchmark() {
    local descriptor=""

    for arg in "$@"; do
        case "${arg}" in
        --descriptor=*)
            descriptor="${arg#*=}"
            ;;
        esac
    done

    [ -z "$descriptor" ] && printf "Missing required argument --descriptor\n" && return 1

    python3 $(dirname $BASH_SOURCE)/../../descriptor-file/descriptor_reader.py $(pwd)/$descriptor | $kubectl apply -f -
}

delete_benchmark() {
    local benchmark_name=""
    local all=""

    for arg in "$@"; do
        case "${arg}" in
        --all)
            all="1"
            ;;
        --name=*)
            benchmark_name="${arg#*=}"
            ;;
        esac
    done

    [ -n "$all" ] && benchmark_name="--all"
    [ -z "$benchmark_name" ] && printf "Missing required argument --name or --all\n" && return 1

    $kubectl delete job $benchmark_name
}

list_benchmarks() {
    $kubectl get jobs --selector app=benchmark-ai -o wide
}

schedule_benchmark() {
    printf "Not yet implemented\n"
}

verb=$1
object=$2

shift
shift

verbose=""
data_dir=./bai

#Common args
for arg in "$@"; do
    case "${arg}" in
    --data-dir=*)
        data_dir="${arg#*=}"
        ;;
    --verbose)
        verbose="1"
        ;;
    esac
done

[ ! -d "$data_dir" ] && mkdir $data_dir

kubeconfig=$(realpath $data_dir/kubeconfig)
kube_config_arg=--kubeconfig=$kubeconfig
kubectl="kubectl ${kube_config_arg}"
terraform_state=$data_dir/terraform.tfstate
terraform_state_arg=--state=$data_dir/terraform.tfstate
terraform_dir=$(dirname $BASH_SOURCE)/cluster
terraform_plan=$data_dir/terraform.plan

terraform_dir=$(realpath $terraform_dir)
terraform_state=$(realpath $terraform_state)
terraform_plan=$(realpath $terraform_plan)

project_dir=$(realpath $(dirname $BASH_SOURCE)/../../..)

case "${object}" in
infra)

    case "${verb}" in
    create)
        create_infra $@
        ;;
    destroy)
        destroy_infra $@
        ;;
    get)
        get_infra $@
        ;;
    validate)
        validate_infra $@
        ;;
    *)
        print_unsupported_verb $object $verb
        ;;
    esac

    ;;
benchmark)

    case "${verb}" in
    run)
        run_benchmark $@
        ;;
    schedule)
        schedule_benchmark $@
        ;;
    get)
        get_benchmark $@
        ;;
    delete)
        delete_benchmark $@
        ;;
    list)
        list_benchmarks $@
        ;;
    *)
        print_unsupported_verb $object $verb
        ;;
    esac
    ;;
*)
    printf "Unknown object"
    ;;
esac
