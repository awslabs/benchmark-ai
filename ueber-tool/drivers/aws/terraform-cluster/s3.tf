resource "aws_s3_bucket" "eks-logs-output" {
  bucket = "eks-logs-output"
  acl    = "private"
  force_destroy = true

  tags = {
    Name = "eks-logs-output"
  }
}

resource "aws_iam_policy" "eks-s3-log-policy" {
  name        = "eks-s3-log-policy"
  path        = "/"
  description = "My test policy"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "${aws_s3_bucket.eks-logs-output.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "${aws_s3_bucket.eks-logs-output.arn}/*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "s3_policy_attachment" {
   policy_arn="${aws_iam_policy.eks-s3-log-policy.arn}"
   role="${module.eks.worker_iam_role_name}"
}

