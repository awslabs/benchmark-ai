terraform {
  required_version = ">= 0.11.8"
}

provider "aws" {
  version = ">= 1.47.0"
  region  = "${var.region}"
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

provider "tls" {
  version = ">= 1.2.0"
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
      name                 = "t3.small_group"
    },
    {
      instance_type        = "c5.large"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "c5.large_group"
    },
    {
      instance_type        = "c5.2xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "c5.2xlarge"
    },
    {
      instance_type        = "c5.4xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "c5.4xlarge"
    },
    {
      instance_type        = "c5.9xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "c5.9xlarge"
    },
    {
      instance_type        = "c5.18xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "c5.18xlarge"
    },
    {
      ami_id               = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
      instance_type        = "p3.2xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "p3.2xlarge_group"
    },
    {
      ami_id               = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
      instance_type        = "p3.8xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "p3.8xlarge_group"
    },
    {
      ami_id               = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
      instance_type        = "p3.16xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "p3.16xlarge_group"
    }
  ]

  worker_groups_count = "11"

  workers_group_defaults = {
    kubelet_extra_args   = "${local.benchmark_kubelet_args}"
    ami_id = "${coalesce(var.eks_cpu_ami_id, data.aws_ami.eks-cpu-optimized.id)}"
    key_name = "${aws_key_pair.worker_key.key_name}"
    asg_min_size         = 0
    asg_desired_capacity = 0
    asg_max_size         = 3
    autoscaling_enabled  = true
  }

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

data "template_file" "ssh_config" {
  template = "${file("${path.module}/template/ssh-config.tpl")}"

  vars = {
    es_endpoint = "${aws_elasticsearch_domain.logs.endpoint}"
    bastion_public_ip = "${aws_instance.bastion.public_ip}"
    bastion_private_key_filename = "${path.cwd}/${local_file.bastion_privatekey_pem.filename}"
    worker_private_key_filename = "${path.cwd}/${local_file.worker_privatekey_pem.filename}"
    # Extracts the first 2 parts of the CIDR: `172.16.0.0/16 => 172.16.*`
    host_wildcard = "${join(".",
                         slice(
                           split(".",
                             element(split("/", module.vpc.vpc_cidr_block), 0)
                           ),
                           0, 2
                         )
                       )
                      }.*"
  }
}
resource "local_file" "ssh_config" {
  content  = "${data.template_file.ssh_config.rendered}"
  filename = "ssh-config"
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
  enable_s3_endpoint = true
  tags               = "${merge(local.tags, map("kubernetes.io/cluster/${var.cluster_name}", "shared"))}"
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
  subnets                              = ["${module.vpc.private_subnets}"]
  tags                                 = "${local.tags}"
  vpc_id                               = "${module.vpc.vpc_id}"
  worker_groups                        = "${local.worker_groups}"
  worker_group_count                   = "${local.worker_groups_count}"
  workers_group_defaults               = "${local.workers_group_defaults}"
  worker_additional_security_group_ids = ["${aws_security_group.all_worker_mgmt.id}"]
  map_roles                            = "${var.map_roles}"
  map_roles_count                      = "${var.map_roles_count}"
  map_users                            = "${var.map_users}"
  map_users_count                      = "${var.map_users_count}"
  map_accounts                         = "${var.map_accounts}"
  map_accounts_count                   = "${var.map_accounts_count}"
}
