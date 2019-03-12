resource "random_id" "s3_bucket_id" {
  keepers = {
    # Generate a new id each time we switch to a new AMI id
    cluster_endpoint = "${module.eks.cluster_endpoint}"
  }

  byte_length = 8
}

resource "aws_s3_bucket" "eks-logs-output" {
  bucket        = "eks-logs-output-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "eks-logs-output"
  }
}

resource "aws_iam_policy" "eks-s3-log-policy" {
  name        = "eks-s3-log-policy"
  path        = "/"
  description = "Worker's policy for the bucket"

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

resource "aws_iam_role_policy_attachment" "log_policy_attachment" {
  policy_arn = "${aws_iam_policy.eks-s3-log-policy.arn}"
  role       = "${module.eks.worker_iam_role_name}"
}
