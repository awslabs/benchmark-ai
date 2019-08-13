#############################################################
# Blackbox tests
#############################################################
resource "aws_iam_role_policy" "code-build-blackbox-tests-role-ec2-actions" {
  name = "blackbox-tests-permissions"
  role = aws_iam_role.code-build-role.name

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
      "Effect": "Allow",
      "Action": "ec2:*",
      "Resource": "*"
      }
    ]
  }
  EOF
}

data "aws_availability_zones" "available" {}

module "blackbox-tests-vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "2.7.0"

  name = "bai-blackbox-tests"
  cidr = "10.0.0.0/16"

  azs = data.aws_availability_zones.available.names
  private_subnets = ["10.0.0.0/24"]
  public_subnets = ["10.0.1.0/24"]

  enable_nat_gateway = true
}

resource "aws_security_group" "blackbox_public" {
  name = "blackbox_public"
  description = "Blackbox public subnet"
  vpc_id = "${module.blackbox-tests-vpc.vpc_id}"

  ingress {
    protocol = -1
    self = true
    from_port = 0
    to_port = 0
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_default_security_group" "default" {
  vpc_id = "${module.blackbox-tests-vpc.vpc_id}"

  ingress {
    protocol = -1
    self = true
    from_port = 0
    to_port = 0
  }

  ingress {
    protocol = -1
    security_groups = ["${aws_security_group.blackbox_public.id}"]
    from_port = 0
    to_port = 0
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


resource "aws_codebuild_project" "ci-blackbox-tests" {
  name = "blackbox-tests"
  description = "Runs blackbox tests"
  build_timeout = "120"
  service_role = aws_iam_role.code-build-role.arn
  badge_enabled = false

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image = var.ci_docker_image["default"]
    type = "LINUX_CONTAINER"
  }

  source {
    type = "CODEPIPELINE"
    buildspec = "blackbox-tests/buildspec.yml"
  }

  vpc_config {
    security_group_ids = [module.blackbox-tests-vpc.default_security_group_id]
    subnets = module.blackbox-tests-vpc.private_subnets
    vpc_id = module.blackbox-tests-vpc.vpc_id
  }
}
