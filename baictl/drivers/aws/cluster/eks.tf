locals {
  # Check the section "The node.type label" at https://github.com/MXNetEdge/benchmark-ai/blob/master/docs/autoscaler-aws.md
  # for an explanation on each type of node.
  bai_worker_kubelet_args   = "--node-labels=node.type=bai-worker"
  k8s_services_kubelet_args  = "--node-labels=node.type=k8s-services"
  bai_services_kubelet_args = "--node-labels=node.type=bai-services"

  other_worker_groups = [
    {
      instance_type        = "t2.small"
      subnets              = "${join(",", slice(module.vpc.private_subnets, 0, 3))}"
      asg_desired_capacity = 2
      asg_max_size         = 10
      asg_min_size         = 1
      name                 = "k8s-services"
      kubelet_extra_args   = "${local.k8s_services_kubelet_args}"
    },
    {
      instance_type        = "m5d.4xlarge"
      subnets              = "${join(",", slice(module.vpc.private_subnets, 0, 3))}"
      asg_desired_capacity = 1
      asg_max_size         = 4
      asg_min_size         = 1
      name                 = "bai-services"
      kubelet_extra_args   = "${local.bai_services_kubelet_args}"
    },
  ]
  # HACK: Terraform versions < 0.12 don't know how to count local lists: https://github.com/hashicorp/terraform/issues/16712
  other_groups_count = 2

  bai_worker_group_instance_types = "${var.benchmark_workers_instance_types}"
  worker_group_subnets = ["${module.vpc.private_subnets}"]
  # HACK: Terraform doesn't know how to count...
  #
  # Which means that this code: `length(module.subnets.private_subnet_ids)` would give the error:
  #
  #     value of count cannot be computed
  #
  # The very detailed explanation on why this happens can be seen here: https://github.com/hashicorp/terraform/issues/12570#issuecomment-366324566
  #
  # The workaround applied is to calculate with values that don't depend on the outputs of the `subnets` module.
  # Given we know that `data.aws_availability_zones` is what we're feeding the `subnets` module then we use it to get
  # the size requested.
  bai_worker_group_subnets_count = "${local.private_subnet_count}"
  bai_worker_groups_count = "${local.bai_worker_group_subnets_count * length(local.bai_worker_group_instance_types)}"

  worker_groups = "${concat(data.null_data_source.bai_worker_groups.*.outputs, local.other_worker_groups)}"
  worker_groups_count = "${local.other_groups_count + local.bai_worker_groups_count}"

  worker_group_tags = {
    k8s-services = [
      {
        key = "k8s.io/cluster-autoscaler/node-template/label/node.type"
        value = "k8s-services"
        propagate_at_launch = true
      }
    ]
    bai-services = [
      {
        key = "k8s.io/cluster-autoscaler/node-template/label/node.type"
        value = "bai-services"
        propagate_at_launch = true
      }
    ]
    default = [
      {
        key = "k8s.io/cluster-autoscaler/node-template/label/node.type"
        value = "bai-worker"
        propagate_at_launch = true
      }
    ]
  }

  workers_group_defaults = {
    ami_id               = "${lookup(local.ami_ids, "cpu")}"
    key_name             = "${aws_key_pair.worker_key.key_name}"
    autoscaling_enabled  = true
  }

  ami_ids = {
    cpu = "${coalesce(var.eks_cpu_ami_id, data.aws_ami.eks-cpu-optimized.id)}"
    gpu = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
  }
}

# The "bai-worker" ASGs.
#
# Assumes that "bai_worker_groups_count = bai_worker_group_instance_types * bai_worker_group_subnets_count" and uses
# basic arithmetic to create each value.
# See the technique explained here: https://serverfault.com/questions/833810/terraform-use-nested-loops-with-count
data "null_data_source" "bai_worker_groups" {
  count = "${local.bai_worker_groups_count}"
  inputs = {
    name = "bai-worker-${element(data.aws_availability_zones.available.names,
                                 count.index % local.bai_worker_group_subnets_count)}-${element(local.bai_worker_group_instance_types,
                                                                                                count.index / local.bai_worker_group_subnets_count)}"
    instance_type = "${element(local.bai_worker_group_instance_types,
                               count.index / local.bai_worker_group_subnets_count)}"
    subnets = "${element(local.worker_group_subnets,
                         count.index % local.bai_worker_group_subnets_count)}"
    ami_id               = "${contains(var.gpu_instance_type_prefixes,
                                       element(split(".",
                                                     element(local.bai_worker_group_instance_types,
                                                             count.index / local.bai_worker_group_subnets_count))
                                               , 0)
                                       )
                              ? lookup(local.ami_ids, "gpu")
                              : lookup(local.ami_ids, "cpu")}"
    kubelet_extra_args   = "${local.bai_worker_kubelet_args}"
    asg_min_size         = 0
    asg_desired_capacity = 0
    asg_max_size         = 10000
  }
}

resource "null_resource" "bai-worker-nodes-cluster-autoscaler-az-tag" {
  count = "${local.bai_worker_groups_count}"
  provisioner "local-exec" {
    command = "aws --region ${var.region} autoscaling create-or-update-tags --tags ResourceId=${element(module.eks.workers_asg_names, count.index + local.other_groups_count)},ResourceType=auto-scaling-group,PropagateAtLaunch=true,Key=k8s.io/cluster-autoscaler/node-template/label/failure-domain.beta.kubernetes.io/zone,Value=${element(data.aws_availability_zones.available.names, count.index % local.bai_worker_group_subnets_count)}"
  }

  triggers {
    workers_asg_names = "${element(module.eks.workers_asg_names, count.index + local.other_groups_count)}"
  }
}

data "aws_ami" "eks-cpu-optimized" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amazon-eks-node-${var.k8s_version}-${var.eks_cpu_ami_version}"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["602401143452"] # AWS EKS account
}

data "aws_ami" "eks-gpu-optimized" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amazon-eks-gpu-node-${var.k8s_version}-${var.eks_gpu_ami_version}"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["602401143452"] # AWS EKS account
}

# Create a private key for each instance that will be a Kubernetes node so we can at least ssh into the box for
# troubleshooting.
resource "tls_private_key" "worker_private_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "worker_key" {
  key_name   = "worker_key"
  public_key = "${tls_private_key.worker_private_key.public_key_openssh}"
}

resource "local_file" "worker_privatekey_pem" {
  content  = "${tls_private_key.worker_private_key.private_key_pem}"
  filename = "worker_private.pem"
  provisioner "local-exec" {
    # HACK while Terraform does not have a proper way to set file permissions: https://github.com/terraform-providers/terraform-provider-local/issues/19
    command = "chmod 400 ${local_file.worker_privatekey_pem.filename}"
  }
}

module "eks" {
  source                               = "terraform-aws-modules/eks/aws"
  cluster_name                         = "${var.cluster_name}"
  # EKS is given a fixed number of subnets.
  #
  # EKS allows to launch worker nodes in subnets that were not specified when
  # creating the EKS cluster as long as all of these subnets have connectivity
  # among themselves (including the "extra").
  #
  # The number of worker subnets is dynamic according to the number of AZs available in
  # the region. So, if EKS is given a fixed amount of subnets, when a new AZ is created,
  # then the EKS cluster does not have to be recreated.
  subnets                              = ["${module.vpc.private_subnets[0]}", "${module.vpc.private_subnets[1]}", "${module.vpc.private_subnets[2]}"]
  cluster_version                      = "${var.k8s_version}"
  tags                                 = "${local.tags}"
  vpc_id                               = "${module.vpc.vpc_id}"
  worker_groups                        = "${local.worker_groups}"
  worker_group_count                   = "${local.worker_groups_count}"
  worker_group_tags                    = "${local.worker_group_tags}"
  workers_group_defaults               = "${local.workers_group_defaults}"
  worker_additional_security_group_ids = ["${aws_security_group.all_worker_mgmt.id}"]
  map_roles                            = "${var.map_roles}"
  map_roles_count                      = "${var.map_roles_count}"
  map_users                            = "${var.map_users}"
  map_users_count                      = "${var.map_users_count}"
  map_accounts                         = "${var.map_accounts}"
  map_accounts_count                   = "${var.map_accounts_count}"
}
