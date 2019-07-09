resource "aws_iam_role" "codepipeline" {
  name = "bai-codepipeline"

  assume_role_policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "codepipeline.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy" "codepipeline-start-builds" {
  name = "codebuild-permissions"
  role = aws_iam_role.codepipeline.name

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Resource": [
          "*"
        ],
        "Action": [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ]
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy_attachment" "codepipeline-attachment" {
  role = aws_iam_role.codepipeline.name
  policy_arn = aws_iam_policy.build-artifacts.arn
}


resource "aws_codepipeline" "codepipeline" {
  name     = "master"
  role_arn = aws_iam_role.codepipeline.arn

  artifact_store {
    location = aws_s3_bucket.build-artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "ThirdParty"
      provider         = "GitHub"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        Owner  = var.github_organization
        Repo   = "benchmark-ai"
        Branch = var.github_branch
      }
    }
  }

  stage {
    name = "Build"

    dynamic "action" {
      for_each = var.projects
      iterator = project

      content {
        name = project.value
        category = "Build"
        owner = "AWS"
        provider = "CodeBuild"
        input_artifacts = ["source_output"]
        output_artifacts = [replace("build_output_${project.value}", "-", "_")]
        version = "1"

        configuration = {
          ProjectName = "${project.value}-master"
        }
      }
    }
  }

  stage {
    name = "Publish"

    dynamic "action" {
      for_each = var.projects
      iterator = project

      content {
        name = project.value
        category = "Build"
        owner = "AWS"
        provider = "CodeBuild"
        input_artifacts = ["source_output"]
        output_artifacts = [replace("publish_output_${project.value}", "-", "_")]
        version = "1"

        configuration = {
          ProjectName = "${project.value}-publish"
        }
      }
    }
  }

  stage {
    name = "CreateInfra"

    action {
      name = "CreateInfra"
      category = "Build"
      owner = "AWS"
      provider = "CodeBuild"
      input_artifacts = ["source_output"]  # To obtain the buildspec
      output_artifacts = []
      version = "1"

      configuration = {
        ProjectName = aws_codebuild_project.ci-create-infra.name
      }
    }
  }

  stage {
    name = "Deploy"

    dynamic "action" {
      for_each = var.projects
      iterator = project

      content {
        name = project.value
        category = "Build"
        owner = "AWS"
        provider = "CodeBuild"
        input_artifacts = ["source_output"]
        output_artifacts = []
        version = "1"

        configuration = {
          ProjectName = "${project.value}-deploy"
        }
      }
    }
  }

  stage {
    name = "blackbox-tests"

    action {
      name = "RunBlackboxTests"
      category = "Build"
      owner = "AWS"
      provider = "CodeBuild"
      input_artifacts = ["source_output"]
      output_artifacts = []
      version = "1"

      configuration = {
        ProjectName = aws_codebuild_project.ci-blackbox-tests.name
      }
    }
  }

  depends_on = [aws_codebuild_project.ci-unit-tests-master, aws_codebuild_project.ci-deploy-master, aws_codebuild_project.ci-publish-master]
}

locals {
  common_environment_variables = {
    for project in var.projects:
    project => {
      ACCOUNT_ID = data.aws_caller_identity.current.account_id
      PROJECT_NAME = project
      DOCKER_REGISTRY = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
    }
  }
}

#############################################################
# Build
#############################################################
resource "aws_codebuild_project" "ci-unit-tests-master" {
  count         = length(var.projects)
  name          = "${var.projects[count.index]}-master"
  description   = "Master build of ${var.projects[count.index]}"
  build_timeout = "30"
  service_role  = aws_iam_role.code-build-role.arn
  badge_enabled = false

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_LARGE"
    image = lookup(
      var.ci_docker_image,
      var.projects[count.index],
      var.ci_docker_image["default"]
    )
    type = "LINUX_CONTAINER"
    privileged_mode = true

    environment_variable {
      name = "RUN_INTEGRATION_TESTS"
      value = tostring(var.run_integration_tests)
    }

    dynamic "environment_variable" {
      for_each = local.common_environment_variables[var.projects[count.index]]
      content {
        name = environment_variable.key
        value = environment_variable.value
      }
    }
  }

  source {
    type = "CODEPIPELINE"
    buildspec = "${var.projects[count.index]}/buildspec.yml"
  }
}

#############################################################
# Publish
#############################################################
resource "aws_codebuild_project" "ci-publish-master" {
  count         = length(var.projects)
  name          = "${var.projects[count.index]}-publish"
  description   = "Publish of ${var.projects[count.index]}"
  build_timeout = "10"
  service_role  = aws_iam_role.code-build-role.arn
  badge_enabled = false

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image = "aws/codebuild/standard:2.0"
    type = "LINUX_CONTAINER"
    privileged_mode = true

    dynamic "environment_variable" {
      for_each = local.common_environment_variables[var.projects[count.index]]
      content {
        name = environment_variable.key
        value = environment_variable.value
      }
    }
  }

  source {
    type = "CODEPIPELINE"
    buildspec = "ci/buildspec-publish.yml"
  }
}


#############################################################
# Deploy
#############################################################
resource "aws_codebuild_project" "ci-deploy-master" {
  count         = length(var.projects)
  name          = "${var.projects[count.index]}-deploy"
  description   = "Deployment of ${var.projects[count.index]}"
  build_timeout = "10"
  service_role  = aws_iam_role.code-build-role.arn
  badge_enabled = false

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image = lookup(
      var.ci_docker_image,
      var.projects[count.index],
      var.ci_docker_image["default"]
    )
    type = "LINUX_CONTAINER"

    dynamic "environment_variable" {
      for_each = local.common_environment_variables[var.projects[count.index]]
      content {
        name = environment_variable.key
        value = environment_variable.value
      }
    }
  }

  source {
    type = "CODEPIPELINE"
    buildspec = "ci/buildspec-deploy.yml"
  }
}


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

data "aws_vpc" "bai-vpc" {
  tags = {
    Name = "test-vpc"
  }
}

data "aws_security_group" "blackbox-tests-security-group" {
  vpc_id = data.aws_vpc.bai-vpc.id
  tags = {
    Name = "benchmark-cluster-eks_worker_sg"
  }
}

data "aws_subnet_ids" "blackbox-tests-security-group" {
  vpc_id = data.aws_vpc.bai-vpc.id
  tags = {
    Visibility = "private"
  }
}

resource "aws_codebuild_project" "ci-blackbox-tests" {
  name          = "blackbox-tests"
  description   = "Runs blackbox tests"
  build_timeout = "120"
  service_role  = aws_iam_role.code-build-role.arn
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
    type            = "CODEPIPELINE"
    buildspec = "blackbox-tests/buildspec.yml"
  }

  vpc_config {
    security_group_ids = [data.aws_security_group.blackbox-tests-security-group.id]
    subnets = data.aws_subnet_ids.blackbox-tests-security-group.ids
    vpc_id = data.aws_vpc.bai-vpc.id
  }
}
