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
    name = "Deploy"

    dynamic "action" {
      for_each = var.projects
      iterator = project

      content {
        name = project.value
        category = "Build"
        owner = "AWS"
        provider = "CodeBuild"
        input_artifacts = ["source_output", replace("publish_output_${project.value}", "-", "_")]
        output_artifacts = []
        version = "1"

        configuration = {
          ProjectName = "${project.value}-deploy"
          PrimarySource = "source_output"
        }
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
      ECR_DOCKER_REGISTRY = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
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
    image = var.ci_docker_image["default"]
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
