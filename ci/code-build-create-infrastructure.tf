#############################################################
# Create infrastructure
#############################################################
resource "aws_iam_role_policy_attachment" "code-build-create-infrastructure-admin" {
  role = aws_iam_role.code-build-role.name
  # HACK: It's not ideal to give admin access, but it's fine for now
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_codebuild_project" "ci-create-infra" {
  name          = "create-infrastructure"
  description   = "Create BAI infrastructure"
  build_timeout = "60"
  service_role  = aws_iam_role.code-build-role.arn
  badge_enabled = false

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = local.bootstrap_image_ecr
    type            = "LINUX_CONTAINER"
    privileged_mode = true

    dynamic "environment_variable" {
      for_each = local.common_environment_variables["baictl"]
      content {
        name  = environment_variable.key
        value = environment_variable.value
      }
    }

    environment_variable {
      name  = "AWS_PREFIX_LIST_ID"
      value = var.prefix_list_id
    }

    # This exposes the VPC gateway of the Blackbox Tests VPC to the Anubis Infrastructure
    environment_variable {
      name  = "EXTRA_CIDR_BLOCK"
      value = "${module.blackbox-tests-vpc.nat_public_ips[0]}/32"
    }

    # These EXTRA_USERS/EXTRA_ROLES gives the provided ARNs permissions on the EKS cluster
    environment_variable {
      name  = "EXTRA_USERS"
      value = signum(length(var.extra_users)) == 1 ? var.extra_users : "UNSET"
    }
    environment_variable {
      name  = "EXTRA_ROLES"
      value = signum(length(var.extra_roles)) == 1 ? var.extra_roles : "UNSET"
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "ci/buildspec-create-infra.yml"
  }
}
