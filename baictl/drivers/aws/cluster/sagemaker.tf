resource "aws_iam_role" "sagemaker-role" {
  name = "bai-sagemaker"
  description = "Role for SageMaker service to assume to execute benchmarks"
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

# Bucket for SageMaker output
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
  policy_arn = "${aws_iam_policy.data-pull-read.arn}"
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

resource "aws_iam_role" "kube2iam-sagemaker-executor-role" {
  name = "sagemaker-executor-role"
  description = "Role for SageMaker executor to assume"
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

resource "aws_iam_role_policy" "sagemaker-can-pass-job-policy" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "${aws_iam_role.sagemaker-role.arn}"
      ],
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "sagemaker.amazonaws.com"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:GetRole"
      ],
      "Resource": [
        "${aws_iam_role.sagemaker-role.arn}"
      ]
    }
  ]
}
EOF
  role = "${aws_iam_role.kube2iam-sagemaker-executor-role.name}"
}

resource "aws_iam_role_policy" "sagemaker-training-job-policy" {
  name = "sagemaker-training-job-policy"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
          "Effect": "Allow",
          "Action": [
              "sagemaker:ListTrainingJobs",
              "sagemaker:DescribeTrainingJob",
              "sagemaker:CreateTrainingJob",
	          "sagemaker:StopTrainingJob"
          ],
          "Resource": "*"
    }
  ]
}
EOF
  role = "${aws_iam_role.kube2iam-sagemaker-executor-role.name}"
}

# Access user scripts - read only
resource "aws_iam_role_policy_attachment" "sagemaker-scripts-attachment" {
  policy_arn = "${aws_iam_policy.script-exchange-read.arn}"
  role       = "${aws_iam_role.kube2iam-sagemaker-executor-role.name}"
}

resource "aws_iam_role_policy_attachment" "sagemaker-output-kube2iam-attachment" {
  policy_arn = "${aws_iam_policy.sagemaker-output-policy.arn}"
  role       = "${aws_iam_role.kube2iam-sagemaker-executor-role.name}"
}

#Dummy object to serve as no-data for SageMaker
resource "aws_s3_bucket_object" "nodata" {
  bucket = "${aws_s3_bucket.data-pull.id}"
  key = "no-data"
  content = "no data"
}
