terraform {
  required_version = ">= 0.11.8"
}

provider "aws" {
  version = ">= 1.47.0"
  region  = "${var.region}"
}

data "aws_availability_zones" "available" {}

locals {
  benchmark_kubelet_args   = "--node-labels=node.type=bechmark-worker"
  autoscaler_kubelet_args  = "--node-labels=node.type=autoscaler"
  datafetcher_kubelet_args = "--node-labels=node.type=datafetcher"

  worker_groups = [
    {
      instance_type        = "t2.small"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = 1
      asg_max_size         = 1
      asg_min_size         = 1
      name                 = "autoscaler.t2.small_group"
      kubelet_extra_args   = "${local.autoscaler_kubelet_args}"
    },
    {
      instance_type        = "m5d.4xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = 1
      asg_max_size         = 4
      asg_min_size         = 1
      name                 = "data-fetcher.m5d.4xlarge_group"
      kubelet_extra_args   = "${local.datafetcher_kubelet_args}"
    },
    {
      instance_type        = "t3.small"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "t3.small_group"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      instance_type        = "c5.large"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "c5.large_group"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      instance_type        = "c5.2xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "c5.2xlarge"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      instance_type        = "c5.4xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "c5.4xlarge"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      instance_type        = "c5.9xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "c5.9xlarge"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      instance_type        = "c5.18xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "c5.18xlarge"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      ami_id               = "${var.eks_gpu_ami}"
      instance_type        = "p3.2xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "p3.2xlarge_group"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      ami_id               = "${var.eks_gpu_ami}"
      instance_type        = "p3.8xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "p3.8xlarge_group"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
    {
      ami_id               = "${var.eks_gpu_ami}"
      instance_type        = "p3.16xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = "0"
      name                 = "p3.16xlarge_group"
      autoscaling_enabled  = true
      asg_max_size         = 3
      asg_min_size         = 0
      kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    },
  ]

  worker_groups_count = "10"

  tags = {
    Environment = "test"
    GithubRepo  = "ci-infrastructure"
    GithubOrg   = "MXNetEdge"
    Workspace   = "${terraform.workspace}"
  }
}

resource "aws_security_group" "worker_group_mgmt_one" {
  name_prefix = "worker_group_mgmt_one"
  description = "SG to be applied to all *nix machines"
  vpc_id      = "${module.vpc.vpc_id}"

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "172.16.0.0/16",
    ]
  }
}

resource "aws_security_group" "worker_group_mgmt_two" {
  name_prefix = "worker_group_mgmt_two"
  vpc_id      = "${module.vpc.vpc_id}"

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "192.168.0.0/16",
    ]
  }
}

resource "aws_security_group" "all_worker_mgmt" {
  name_prefix = "all_worker_management"
  vpc_id      = "${module.vpc.vpc_id}"

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "172.16.0.0/12",
      "192.168.0.0/16",
    ]
  }
}

module "vpc" {
  source             = "terraform-aws-modules/vpc/aws"
  version            = "1.14.0"
  name               = "test-vpc"
  cidr               = "172.16.0.0/16"
  azs                = ["${data.aws_availability_zones.available.names[0]}", "${data.aws_availability_zones.available.names[1]}", "${data.aws_availability_zones.available.names[2]}"]
  private_subnets    = ["172.16.0.0/20", "172.16.16.0/20", "172.16.32.0/20"]
  public_subnets     = ["172.16.48.0/20", "172.16.64.0/20", "172.16.80.0/20"]
  enable_nat_gateway = true
  single_nat_gateway = true
  tags               = "${merge(local.tags, map("kubernetes.io/cluster/${var.cluster_name}", "shared"))}"
}

module "eks" {
  source                               = "terraform-aws-modules/eks/aws"
  cluster_name                         = "${var.cluster_name}"
  subnets                              = ["${module.vpc.private_subnets}"]
  tags                                 = "${local.tags}"
  vpc_id                               = "${module.vpc.vpc_id}"
  worker_groups                        = "${local.worker_groups}"
  worker_group_count                   = "${local.worker_groups_count}"
  worker_additional_security_group_ids = ["${aws_security_group.all_worker_mgmt.id}"]
  map_roles                            = "${var.map_roles}"
  map_roles_count                      = "${var.map_roles_count}"
  map_users                            = "${var.map_users}"
  map_users_count                      = "${var.map_users_count}"
  map_accounts                         = "${var.map_accounts}"
  map_accounts_count                   = "${var.map_accounts_count}"
}
