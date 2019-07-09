resource "aws_s3_bucket" "scripts-exchange" {
  bucket        = "scripts-exchange-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "scripts-exchange"
  }
}

resource "aws_iam_role_policy" "bai-bff-pod-role-s3-policy" {
  name = "s3-permissions"
  role = aws_iam_role.kube2iam-bff-pod-role.name

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Resource": [
          "${aws_s3_bucket.scripts-exchange.arn}"
        ],
        "Action": [
          "s3:*"
        ]
      }
    ]
  }
  EOF
}

resource "aws_iam_role" "kube2iam-bff-pod-role" {
  name = "bai-bff-pod-role"
  assume_role_policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "${module.eks.worker_iam_role_arn}"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  EOF
}
