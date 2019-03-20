#!/bin/bash

complete -W "create destroy run delete schedule list infra benchmark validate --all --name= --descriptor= --target= aws --aws-es --aws-bastion-ip --aws-cluster --aws-region= --nodes --data-dir --no-validate" baictl
