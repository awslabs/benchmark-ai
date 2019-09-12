resource "aws_ecr_repository" "ecr" {
  count = length(var.projects)
  name  = var.projects[count.index]
}

resource "aws_ecr_repository" "ecr_bootstrap" {
  name = "bootstrap-image"
}

resource "aws_ecr_repository_policy" "codebuild-policy-bootstrap-image" {
  repository = "${aws_ecr_repository.ecr_bootstrap.name}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CodeBuildAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com" 
      },
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ]
    }
  ]
}
EOF
}
