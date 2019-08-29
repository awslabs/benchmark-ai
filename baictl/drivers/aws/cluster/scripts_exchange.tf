resource "aws_s3_bucket" "scripts-exchange" {
  bucket        = "scripts-exchange-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "scripts-exchange"
  }
}

resource "aws_iam_policy" "script-exchange-read" {
  name   = "script-exchange-read"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "${aws_s3_bucket.scripts-exchange.arn}"
      ],
      "Action": [
        "s3:ListBucket"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
        "${aws_s3_bucket.scripts-exchange.arn}/*"
      ],
      "Action": [
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:GetObjectVersion",
        "s3:GetObjectVersionTagging"
      ]
    }
  ]
}
EOF
}

resource "aws_iam_policy" "script-exchange-write" {
  name   = "script-exchange-write"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "${aws_s3_bucket.scripts-exchange.arn}/*"
      ],
      "Action": [
        "s3:PutObject",
        "s3:PutObjectTagging",
        "s3:PutObjectVersionTagging"
      ]
    }
  ]
}
EOF
}

resource "aws_iam_role" "kube2iam-bff-pod-role" {
  name               = "bai-bff-pod-role"
  assume_role_policy = <<EOF
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

resource "aws_iam_role_policy_attachment" "bai-bff-read-script-exchange" {
  policy_arn = "${aws_iam_policy.script-exchange-read.arn}"
  role       = "${aws_iam_role.kube2iam-bff-pod-role.name}"
}

resource "aws_iam_role_policy_attachment" "bai-bff-write-script-exchange" {
  policy_arn = "${aws_iam_policy.script-exchange-write.arn}"
  role       = "${aws_iam_role.kube2iam-bff-pod-role.name}"
}

resource "aws_iam_role_policy_attachment" "bai-bff-dynamodb-rwc" {
  policy_arn = "${aws_iam_policy.anubis_table_rwc.arn}"
  role       = "${aws_iam_role.kube2iam-bff-pod-role.name}"
}
