#!/bin/bash

print_unsupported_verb() {
    local object=$1
    local verb=$2
    printf "Unsupported verb ${verb} for object ${object}\n"
}

create_infra() {
    local cluster_name=""
    local region=""

    for arg in "$@"; do
        case "${arg}" in
        --name=*)
            cluster_name="${arg#*=}"
            ;;
        --aws-region=*)
            region="${arg#*=}"
            ;;
        esac
    done

    cd $data_dir

    local vars=""

    [ -n "$cluster_name" ] && vars="${vars} -var 'cluster-name=${cluster_name}'"
    [ -n "$region" ] && vars="${vars} -var 'region=${region}'"

    terraform init $terraform_dir
    terraform get $terraform_dir

    terraform plan --state=$terraform_state --out=$terraform_plan ${vars} $terraform_dir
    terraform apply $terraform_plan
    terraform output kubectl_config >kubeconfig

    #Make private key not public accessible
    local jumper_pem=$(terraform output jumper_pem)
    chmod 400 $jumper_pem

    $kubectl apply -f fluentd-daemonset.yaml
    $kubectl apply -f autoscaler-deployment.yaml
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
        --aws-jumper)
            terraform output --state=$terraform_state jumper_public_ip
            ;;    
        esac
    done
    printf "\n----------\n"
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

    local jumper_pem=$(terraform output --state=$terraform_state jumper_pem)
    local jumper_ip=$(terraform output --state=$terraform_state jumper_public_ip)
    local es_endpoint=$(terraform output --state=$terraform_state es_endpoint)

    local query_body="{\"from\" : 0, \"size\" : 1000,\"query\" : {\"term\" : { \"kubernetes.labels.job-name\":\"${benchmark_name}\" }}}"

    local curl_cmd="curl -X POST -s -H 'Content-Type: application/json' -d '$query_body' ${es_endpoint}/_search"

    ssh -q -o StrictHostKeyChecking=no -i $data_dir/$jumper_pem ubuntu@$jumper_ip "${curl_cmd}" | jq '.hits.hits[]._source | "(\(."@timestamp") \(.log)"' -j | sort
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

    for arg in "$@"; do
        case "${arg}" in
        --name=*)
            benchmark_name="${arg#*=}"
            ;;
        esac
    done

    [ -z "$benchmark_name" ] && printf "Missing required argument --name\n" && return 1

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
terraform_dir=$(dirname $BASH_SOURCE)/terraform-cluster
terraform_plan=$data_dir/terraform.plan

terraform_dir=$(realpath $terraform_dir)
terraform_state=$(realpath $terraform_state)
terraform_plan=$(realpath $terraform_plan)

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
    *)
        print_unsupported_verb $object $verb
        ;;
    esac
    ;;

benchmarks)

    case "${verb}" in
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
