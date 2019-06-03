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
        Owner  = "MXNetEdge"
        Repo   = "benchmark-ai"
        Branch = "master"
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
        output_artifacts = ["build_output-${project.value}"]
        version = "1"

        configuration = {
          ProjectName = "${project.value}-master"
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
        input_artifacts = ["build_output-${project.value}"]
        output_artifacts = []
        version = "1"

        configuration = {
          ProjectName = "${project.value}-deploy"
        }
      }
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
  build_timeout = "10"
  service_role  = aws_iam_role.code-build-role.arn
  badge_enabled = true

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image = lookup(
      var.ci_docker_image,
      var.projects[count.index],
      var.ci_docker_image["default"]
    )
    type = "LINUX_CONTAINER"
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/MXNetEdge/benchmark-ai.git"
    git_clone_depth = 1
    auth {
      type = "OAUTH"
    }
    buildspec = data.template_file.buildspec-build[count.index].rendered
    report_build_status = true
  }

  tags = {
    GithubRepo = "benchmark-ai"
    GithubOrg  = "MXNetEdge"
    Workspace  = terraform.workspace
  }
}

data "template_file" "buildspec-build" {
  count = length(var.projects)
  template = file("buildspec-build.tpl.yml")

  vars = {
    project = var.projects[count.index]
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
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image = var.ci_docker_image["default"]
    type = "LINUX_CONTAINER"
  }

  source {
    type = "NO_SOURCE"
    buildspec = data.template_file.buildspec-deploy[count.index].rendered
  }

  tags = {
    GithubRepo = "benchmark-ai"
    GithubOrg  = "MXNetEdge"
    Workspace  = terraform.workspace
  }
}

data "template_file" "buildspec-deploy" {
  count = length(var.projects)
  template = file("buildspec-deploy.tpl.yml")

  vars = {
    project = var.projects[count.index]
  }
}
