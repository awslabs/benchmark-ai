#!/bin/bash

print_usage_and_exit(){
    echo "Usage: baictl [verb] [object] [options]"
    exit 1
}

all_args="$@"

verb=$1
object=$2

if ! [[ $verb =~ ^(create|destroy|get|list|run|schedule)$ ]]
    then print_usage_and_exit
fi

if ! [[ $object =~ ^(infra|benchmarks?)$ ]]
    then print_usage_and_exit
fi

verbose=0
data_dir=./bai  

for arg in "$@" 
do
    case "${arg}" in
    --target=*)
      target="${arg#*=}"
      ;;
    --data-dir=*)
      data_dir="${arg#*=}"
      ;;
    --verbose)
      verbose=1
      ;;
  esac
done

saved_target=$data_dir/.target

echo $saved_target

if [ -f $saved_target ]; then
    target=$(<$saved_target)
fi

target="${target:=aws}"

backend=$(dirname $BASH_SOURCE)/drivers/$target/baidriver.sh

if [ -f $backend ]; then
   ${backend} "$@" || print_usage_and_exit
else
   echo "Backend $target does not exist."
   print_usage_and_exit
fi

