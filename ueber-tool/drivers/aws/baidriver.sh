#!/bin/bash

print_unsupported_verb()
{
    local object=$1
    local verb=$2
    echo "Unsupported verb ${verb} for object ${object}"
}

create_infra(){
    echo "Create infra"

    cd $data_dir

    terraform plan --state=$terraform_state --out=$terraform_plan $terraform_dir
    terraform apply $terraform_plan

    terraform output kubectl_config > kubeconfig

    #Make private key no public accessible
    local jumper_pem=$(terraform output jumper_pem)
    chmod 400 $jumper_pem

    $kubectl apply -f fluentd-daemonset.yaml
    $kubectl apply -f autoscaler-deployment.yaml
}

destroy_infra(){
    echo "Destroy infra"
    terraform init $terraform_dir
    terraform get $terraform_dir
    terraform plan --destroy --state=$terraform_state $terraform_dir
    terraform destroy --state=$terraform_state $terraform_dir
}

get_infra(){
    echo "Get infra"
    echo "Running nodes"
    $kubectl get nodes --show-labels
    terraform show $terraform_state
}

get_benchmark(){
    local jumper_pem=$(terraform output --state=$terraform_state jumper_pem)
    local jumper_ip=$(terraform output --state=$terraform_state jumper_public_ip)
    local es_endpoint=$(terraform output --state=$terraform_state es_endpoint)

    echo $jumper_pem
    echo $jumper_ip
    echo $es_endpoint

    ssh -i $data_dir/$jumper_pem ubuntu@$jumper_ip "curl -s ${es_endpoint}" | jq
}


echo AWS driver
echo "$@"

verb=$1
object=$2

verbose=0
data_dir=./bai  

#Common args
for arg in "$@" 
do
    case "${arg}" in
    --data-dir=*)
      data_dir="${arg#*=}"
      ;;
    --verbose)
      verbose=1
      ;;
  esac
done

kubeconfig=$(grealpath $data_dir/kubeconfig)
kube_config_arg=--kubeconfig=$kubeconfig
kubectl="kubectl ${kube_config_arg}"
terraform_state=$data_dir/terraform.tfstate
terraform_state_arg=--state=$data_dir/terraform.tfstate
terraform_dir=$(dirname $BASH_SOURCE)/terraform-cluster
terraform_plan=$data_dir/terraform.plan

terraform_dir=$(grealpath $terraform_dir)
terraform_state=$(grealpath $terraform_state)
terraform_plan=$(grealpath $terraform_plan)


case "${object}" in
    infra)
    
    case "${verb}" in
        create)
        create_infra
        ;;
        destroy)
        destroy_infra
        ;;
        get)
        get_infra
        ;;
        *)
        print_unsupported_verb $object $verb
    esac

    ;;
    benchmark)

    case "${verb}" in
        run)
        run_benchmark
        ;;
        schedule)
        schedule_benchmark
        ;;
        get)
        get_benchmark
        ;;
        *)
        print_unsupported_verb $object $verb
    esac
    ;;

    benchmarks)

    case "${verb}" in
        list)
        list_benchmarks
        ;;
        *)
        print_unsupported_verb $object $verb
    esac

    ;;
    *)
    echo "Unknown object"
esac


