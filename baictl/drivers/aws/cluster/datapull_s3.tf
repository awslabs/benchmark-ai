resource "aws_s3_bucket" "data-pull" {
  bucket        = "data-pull-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "data-pull"
  }
}

resource "aws_iam_policy" "data-pull-policy" {
  name        = "data-pull-policy"
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
      "Resource": "${aws_s3_bucket.data-pull.arn}"
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
      "Resource": "${aws_s3_bucket.data-pull.arn}/*"
    }
  ]
}
EOF
}

resource "aws_iam_role" "kube2iam-data-puller-role" {
  name = "data-puller"
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
  policy_arn = "${aws_iam_policy.data-pull-policy.arn}"
  role       = "${aws_iam_role.kube2iam-data-puller-role.name}"
}
