terraform {
  required_version = ">= 0.11.8"

  backend "s3" {
    bucket = "bai-terraform-remote-state"
    key    = "ci/terraform.tfstate"
    region = "us-east-1"
  }
}

data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "bai-terraform-remote-state"
    key    = "ci-state-${var.region}/terraform.tfstate"
    region = "${var.region}"
  }
}

resource "aws_s3_bucket" "terraform-state-storage-s3" {
  bucket = "bai-terraform-remote-state"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  tags {
    Name = "S3 Remote Terraform State Store"
  }
}

provider "aws" {
  version = ">= 2.4.0"
  region  = "${var.region}"
  allowed_account_ids = [
    563267192464  # bai-gamma@amazon.com
  ]
}

resource "aws_iam_role" "code-build-role" {
  name = "code-build-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "code-build-role-policy" {
  role = "${aws_iam_role.code-build-role.name}"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    }
  ]
}
POLICY
}


resource "aws_codebuild_project" "ci-unit-tests" {
  count = "${length(var.projects)}"
  name          = "${element(var.projects, count.index)}"
  description   = "Unit tests build of ${element(var.projects, count.index)}"
  build_timeout = "10"
  service_role  = "${aws_iam_role.code-build-role.arn}"
  badge_enabled = true

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "conda/miniconda3"
    type                        = "LINUX_CONTAINER"
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/MXNetEdge/benchmark-ai.git"
    git_clone_depth = 1
    auth = {
      type = "OAUTH"
    }
    buildspec = "${element(var.projects, count.index)}/buildspec.yml"
    report_build_status = true
  }

  tags = {
    GithubRepo  = "benchmark-ai"
    GithubOrg   = "MXNetEdge"
    Workspace   = "${terraform.workspace}"
  }
}


resource "aws_codebuild_project" "ci-unit-tests-master" {
  count = "${length(var.projects)}"
  name          = "${element(var.projects, count.index)}-master"
  description   = "Unit tests master build of ${element(var.projects, count.index)}"
  build_timeout = "10"
  service_role  = "${aws_iam_role.code-build-role.arn}"
  badge_enabled = true

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "conda/miniconda3"
    type                        = "LINUX_CONTAINER"
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/MXNetEdge/benchmark-ai.git"
    git_clone_depth = 1
    auth = {
      type = "OAUTH"
    }
    buildspec = "${element(var.projects, count.index)}/buildspec.yml"
    report_build_status = true
  }

  tags = {
    GithubRepo  = "benchmark-ai"
    GithubOrg   = "MXNetEdge"
    Workspace   = "${terraform.workspace}"
  }
}

resource "aws_codebuild_webhook" "ci-unit-tests" {
  count = "${length(var.projects)}"
  project_name = "${element(aws_codebuild_project.ci-unit-tests.*.name, count.index)}"
}

resource "aws_codebuild_webhook" "ci-unit-tests-master" {
  count = "${length(var.projects)}"
  project_name = "${element(aws_codebuild_project.ci-unit-tests-master.*.name, count.index)}"
}

locals {
  filter_groups_prs = [
    {
      type = "EVENT"
      pattern = "PULL_REQUEST_CREATED, PULL_REQUEST_UPDATED, PULL_REQUEST_REOPENED"
    },
  ]
  filter_groups_master = [
    {
      type = "EVENT"
      pattern = "PUSH"
    },
    {
      type = "HEAD_REF"
      pattern = "refs/heads/master$"
    },
  ]
}

# TODO: Still not supported by AWS provider in Terraform: https://github.com/terraform-providers/terraform-provider-aws/issues/7503
resource "null_resource" "ci-unit-tests-filter" {
  count = "${length(var.projects)}"
  provisioner "local-exec" {
    command = "aws --region ${var.region} codebuild update-webhook --project-name ${self.triggers.project_name} --filter-groups '[${self.triggers.filter_groups}]'"
  }

  triggers {
    project_name = "${element(aws_codebuild_webhook.ci-unit-tests.*.project_name, count.index)}"
    filter_groups = "${jsonencode(local.filter_groups_prs)}"
  }
}

resource "null_resource" "ci-unit-tests-master-filter" {
  count = "${length(var.projects)}"
  provisioner "local-exec" {
    command = "aws --region ${var.region} codebuild update-webhook --project-name ${self.triggers.project_name} --filter-groups '[${self.triggers.filter_groups}]'"
  }

  triggers {
    project_name = "${element(aws_codebuild_webhook.ci-unit-tests-master.*.project_name, count.index)}"
    filter_groups = "${jsonencode(local.filter_groups_master)}"
  }
}
