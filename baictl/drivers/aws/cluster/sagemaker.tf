                                                                                resource "aws_iam_role" "sagemaker-role" {
  name = "bai-sagemaker"
  assume_role_policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sagemaker.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
  }
  EOF
}

resource "aws_s3_bucket" "sagemaker-output" {
  bucket        = "sagemaker-output-${random_id.s3_bucket_id.hex}"
  acl           = "private"
  force_destroy = true

  tags = {
    Name = "data-pull"
  }
}

resource "aws_iam_policy" "sagemaker-output-policy" {
  name        = "sagemaker-output-policy"
  path        = "/"
  description = "Private SageMaker bucket policy"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": "${aws_s3_bucket.sagemaker-output.arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": "${aws_s3_bucket.sagemaker-output.arn}/*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "sagemaker-data-pull-policy-attachment" {
  policy_arn = "${aws_iam_policy.data-pull-policy.arn}"
  role       = "${aws_iam_role.sagemaker-role.name}"
}

resource "aws_iam_role_policy_attachment" "sagemaker-data-output-attachment" {
  policy_arn = "${aws_iam_policy.sagemaker-output-policy.arn}"
  role       = "${aws_iam_role.sagemaker-role.name}"
}

resource "aws_iam_role_policy_attachment" "sagemaker-full-access-attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
  role       = "${aws_iam_role.sagemaker-role.name}"
}