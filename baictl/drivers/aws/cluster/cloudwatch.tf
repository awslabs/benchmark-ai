
resource "aws_iam_role" "kube2iam-cloudwatch-exporter-pod-role" {
  name = "cloudwatch-exporter"
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


resource "aws_iam_policy" "cloudwatch-put-metrics" {
  name        = "cloudwatch-put-metrics"
  path        = "/"
  description = "Exporter's policy to put metrics in cloudwatch"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
                "cloudwatch:PutMetricData",
                "cloudwatch:ListDashboards",
                "cloudwatch:GetDashboard",
                "cloudwatch:PutDashboard"
            ],
            "Resource": "*"
    }
  ]
}
EOF
}


resource "aws_iam_role_policy_attachment" "kube2iam-cloudwatch-exporter-pod-role-put-metrics" {
  policy_arn = "${aws_iam_policy.cloudwatch-put-metrics.arn}"
  role       = "${aws_iam_role.kube2iam-cloudwatch-exporter-pod-role.name}"
}