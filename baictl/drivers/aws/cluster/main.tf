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
