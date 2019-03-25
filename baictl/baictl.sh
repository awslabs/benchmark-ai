#!/bin/bash

print_usage_and_exit(){
    printf "Usage: baictl [verb] [object] [options]\n"
    exit 1
}

all_args="$@"

verb=$1
object=$2

if ! [[ $verb =~ ^(create|destroy|get|list|run|schedule|delete|validate)$ ]]
    then print_usage_and_exit
fi

if ! [[ $object =~ ^(infra|benchmarks?)$ ]]
    then print_usage_and_exit
fi

verbose=""
just_help=""
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
    --help)
        just_help="1"
  esac
done

saved_target=$data_dir/.target

if [ -f $saved_target ]; then
    target=$(<$saved_target)
fi

target="${target:=aws}"

if [ -L $BASH_SOURCE ] ; then
    dir=$(dirname "$(readlink -n $BASH_SOURCE)")
else
    dir=$(dirname $BASH_SOURCE)
fi

backend=$dir/drivers/$target/baidriver.sh

if [ -f $backend ]; then
   ${backend} "$@" || print_usage_and_exit
else
   printf "Backend %s does not exist.\n" "$target"
   print_usage_and_exit
fi

