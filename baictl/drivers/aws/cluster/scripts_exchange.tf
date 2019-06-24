resource "aws_s3_bucket" "scripts-exchange" {
  bucket        = "scripts-exchange-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "scripts-exchange"
  }
}

resource "aws_iam_policy" "scripts-exchange-policy" {
  name        = "scripts-exchange-policy"
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
      "Resource": "${aws_s3_bucket.scripts-exchange.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",

        "s3:PutObjectTagging",
        "s3:GetObjectTagging",

        "s3:GetObjectVersion",

        "s3:GetObjectVersionTagging",
        "s3:PutObjectVersionTagging"
      ],
      "Resource": "${aws_s3_bucket.scripts-exchange.arn}/*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "data_pull_policy_attachment" {
  policy_arn = "${aws_iam_policy.scripts-exchange-policy.arn}"
  role       = "${module.eks.worker_iam_role_name}"
}
