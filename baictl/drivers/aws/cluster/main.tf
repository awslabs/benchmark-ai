terraform {
  required_version = ">= 0.11.8"
}

provider "aws" {
  version = ">= 1.47.0"
  region  = "${var.region}"
}

provider "tls" {
  version = ">= 1.2.0"
}

data "aws_availability_zones" "available" {}

# TODO: AWS provider should provide the defaults tags: https://github.com/terraform-providers/terraform-provider-aws/issues/7926
locals {
  tags = {
    Environment = "test"
    GithubRepo  = "ci-infrastructure"
    GithubOrg   = "MXNetEdge"
    Workspace   = "${terraform.workspace}"
  }
  vpc_cidr_block = "172.16.0.0/16"
  bits = 4
  maximum_subnets = "${256 / pow(2, local.bits)}"
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
      "${local.vpc_cidr_block}",
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
  azs                = ["${data.aws_availability_zones.available.names[0]}", "${data.aws_availability_zones.available.names[1]}", "${data.aws_availability_zones.available.names[2]}"]
  private_subnets    = ["${cidrsubnet(local.vpc_cidr_block, local.bits, 0)}",
                        "${cidrsubnet(local.vpc_cidr_block, local.bits, 1)}",
                        "${cidrsubnet(local.vpc_cidr_block, local.bits, 2)}"]
  cidr               = "${local.vpc_cidr_block}"
  # The number of public subnets is fixed because we don't launch worker nodes on them. It's going to host only the
  # BAI services.
  # Also, these subnets are at the end of the CIDR block so that they don't conflict with the expanding private subnets.
  # This logic breaks when number of azs in a region is larger than 12.
  public_subnets     = ["${cidrsubnet(local.vpc_cidr_block, local.bits, local.maximum_subnets - 3)}",
                        "${cidrsubnet(local.vpc_cidr_block, local.bits, local.maximum_subnets - 2)}",
                        "${cidrsubnet(local.vpc_cidr_block, local.bits, local.maximum_subnets - 1)}"]

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_s3_endpoint = true
  # The specific kubernetes.io/cluster/* resource tags below are required
  # for EKS and Kubernetes to discover and manage networking resources
  # https://www.terraform.io/docs/providers/aws/guides/eks-getting-started.html#base-vpc-networking
  tags               = "${merge(local.tags, map("kubernetes.io/cluster/${var.eks_cluster_name}", "shared"))}"
}

resource "aws_msk_cluster" "benchmark-msk-cluster" {
  depends_on             = ["module.vpc"]
  name                   = "${var.msk_cluster_name}"
  broker_count           = "${var.msk_broker_count}"
  broker_instance_type   = "${var.msk_broker_instance_type}"
  broker_security_groups = ["${list(module.vpc.default_security_group_id)}"]
  broker_volume_size     = "${var.msk_broker_volume_size}"
  client_subnets         = ["${module.vpc.private_subnets}"]
  kafka_version          = "${var.msk_kafka_version}"
}
