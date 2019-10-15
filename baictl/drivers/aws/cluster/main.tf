terraform {
  required_version = ">= 0.11.8"
  backend          "s3"             {}
}

provider "aws" {
  version = "~> 2.17.0"
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
    GithubOrg   = "awslabs"
    Workspace   = "${terraform.workspace}"
  }

  private_subnet_count = "${length(data.aws_availability_zones.available.names)}"
  vpc_cidr_block       = "172.16.0.0/16"
  bits                 = 4
  maximum_subnets      = "${256 / pow(2, local.bits)}"

  msk_subnet_count = 3
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

resource "aws_security_group" "bff_external_access" {
  name        = "anubis_bff_external_access"
  description = "bff_external_access"
  vpc_id      = "${module.vpc.vpc_id}"

  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    prefix_list_ids = "${var.prefix_list_ids}"
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = "${var.ssh_access_cidr_blocks}"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags {
    "Name" = "anubis_bff_external_access"
  }
}

data "template_file" "ssh_config" {
  template = "${file("${path.module}/template/ssh-config.tpl")}"

  vars = {
    es_endpoint                  = "${aws_elasticsearch_domain.logs.endpoint}"
    bastion_public_ip            = "${aws_instance.bastion.public_ip}"
    bastion_private_key_filename = "${local_file.bastion_privatekey_pem.filename}"
    worker_private_key_filename  = "${local_file.worker_privatekey_pem.filename}"

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
  filename = "${var.data_dir}/ssh-config"
}

data "null_data_source" "subnets" {
  count = "${local.private_subnet_count}"

  inputs = {
    private_cidr_block = "${cidrsubnet(local.vpc_cidr_block, 4, count.index)}"
  }
}

module "vpc" {
  source          = "terraform-aws-modules/vpc/aws"
  version         = "1.14.0"
  name            = "test-vpc"
  cidr            = "${local.vpc_cidr_block}"
  azs             = ["${data.aws_availability_zones.available.names}"]
  private_subnets = ["${data.null_data_source.subnets.*.outputs.private_cidr_block}"]

  # The number of public subnets is fixed because we don't launch worker nodes on them. It's going to host only the
  # BAI services.
  # Also, these subnets are at the end of the CIDR block so that they don't conflict with the expanding private subnets.
  # This logic breaks when number of azs in a region is larger than 12.
  public_subnets = ["${cidrsubnet(local.vpc_cidr_block, local.bits, local.maximum_subnets - 3)}",
    "${cidrsubnet(local.vpc_cidr_block, local.bits, local.maximum_subnets - 2)}",
    "${cidrsubnet(local.vpc_cidr_block, local.bits, local.maximum_subnets - 1)}",
  ]

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_s3_endpoint = true

  # The specific kubernetes.io/cluster/* resource tags below are required
  # for EKS and Kubernetes to discover and manage networking resources
  # https://www.terraform.io/docs/providers/aws/guides/eks-getting-started.html#base-vpc-networking
  tags = "${merge(local.tags, map("kubernetes.io/cluster/${var.cluster_name_prefix}", "shared"))}"

  private_subnet_tags = {
    Visibility = "private"
  }

  public_subnet_tags = {
    Visibility = "public"
  }
}

resource "aws_msk_cluster" "benchmark-msk-cluster" {
  depends_on             = ["module.vpc"]
  cluster_name           = "${var.cluster_name_prefix}"
  kafka_version          = "${var.msk_kafka_version}"
  number_of_broker_nodes = "${var.msk_brokers_per_az * local.msk_subnet_count}"

  broker_node_group_info {
    instance_type   = "${var.msk_broker_instance_type}"
    ebs_volume_size = "${var.msk_broker_volume_size}"

    client_subnets = ["${slice(module.vpc.private_subnets, 0, local.msk_subnet_count)}"]

    security_groups = [
      "${module.eks.worker_security_group_id}",
      "${aws_security_group.loopback.id}",
      "${aws_security_group.ssh-access-rules.id}",
    ]
  }

  encryption_info {
    encryption_in_transit = {
      client_broker = "PLAINTEXT"
      in_cluster = false
    }
  }
}

resource "aws_dynamodb_table" "anubis_client_job_status_table" {
  name           = "AnubisClientJobStatus"
  billing_mode   = "PROVISIONED"
  read_capacity  = 30
  write_capacity = 30
  hash_key       = "ActionId"
  range_key      = "TimestampMessageId"

  attribute {
    name = "ActionId"
    type = "S"
  }

  attribute {
    name = "TimestampMessageId"
    type = "S"
  }

  tags = {
    Name        = "anubis_client_job_status_table"
  }
}

resource "aws_dynamodb_table" "anubis_client_jobs_table" {
  name           = "AnubisClientJobs"
  billing_mode   = "PROVISIONED"
  read_capacity  = 30
  write_capacity = 30
  hash_key       = "ClientId"
  range_key      = "TimestampActionId"

  attribute {
    name = "ClientId"
    type = "S"
  }

  attribute {
    name = "TimestampActionId"
    type = "S"
  }

  tags = {
    Name        = "anubis_client_jobs_table"
  }
}

# TODO: restrict policy to only point to anubis_client_job_status_table and anubis_jobs_table
resource "aws_iam_policy" "anubis_table_rwc" {
  name        = "anubis_table_rwc"
  description = "Allow for read/write/create on DynamoDB"

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:PutItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "dynamodb:Query",
            "Resource": "arn:aws:dynamodb:*:*:table/*/index/*"
        }
    ]
}
EOF
}


