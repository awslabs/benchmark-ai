#!/bin/bash

complete -W "create destroy run delete schedule list validate infra benchmark get show k8s-dashboard port-forward --all --name= --descriptor= --target= aws --aws-es --aws-bastion-ip --aws-cluster --aws-region= --nodes --data-dir --no-validate" baictl
