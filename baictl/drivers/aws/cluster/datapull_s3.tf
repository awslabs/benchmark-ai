resource "aws_s3_bucket" "data-pull" {
  bucket        = "data-pull-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "data-pull"
  }
}

resource "aws_iam_policy" "data-pull-read" {
  name        = "data-pull-read"
  path        = "/"
  description = "Worker's read policy for the bucket"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "${aws_s3_bucket.data-pull.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:GetObjectVersion",
        "s3:GetObjectVersionTagging"
      ],
      "Resource": "${aws_s3_bucket.data-pull.arn}/*"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "data-pull-write" {
  name        = "data-pull-write"
  path        = "/"
  description = "Worker's write policy for the bucket"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "${aws_s3_bucket.data-pull.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectTagging",
        "s3:PutObjectVersionTagging"
      ],
      "Resource": "${aws_s3_bucket.data-pull.arn}/*"
    }
  ]
}
EOF
}

resource "aws_iam_role" "kube2iam-benchmark-host" {
  name = "benchmark-host"
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

resource "aws_iam_role_policy_attachment" "data_pull_policy_attachment" {
  policy_arn = "${aws_iam_policy.data-pull-read.arn}"
  role       = "${aws_iam_role.kube2iam-benchmark-host.name}"
}

resource "aws_iam_role_policy_attachment" "data_pull_script_policy_attachment" {
  policy_arn = "${aws_iam_policy.script-exchange-read.arn}"
  role       = "${aws_iam_role.kube2iam-benchmark-host.name}"
}
