resource "aws_iam_role" "kube2iam-fluentd-pod-role" {
  name = "bai-fluentd-pod"
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

resource "aws_iam_role_policy" "kube2iam-fluentd-pod-role-policy" {
  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:*"
        ],
        "Resource": [
          "${aws_s3_bucket.eks-logs-output.arn}",
          "${aws_s3_bucket.eks-logs-output.arn}/*"
        ]
      }
    ]
  }
  EOF
  name = "s3-at-eks-logs-bucket"
  role = "${aws_iam_role.kube2iam-fluentd-pod-role.name}"
}

data "template_file" "fluentd-daemonset" {
  template = "${file("${path.module}/template/fluentd-daemonset.tpl.yaml")}"

  vars = {
    cluster_region      = "${var.region}"
    cluster_es_endpoint = "${aws_elasticsearch_domain.logs.endpoint}"
    cluster_log_bucket  = "${aws_s3_bucket.eks-logs-output.bucket}"
    kube2iam_pod_role_name = "${aws_iam_role.kube2iam-fluentd-pod-role.name}"
  }
}

resource "local_file" "fluentd-daemonset" {
  content  = "${data.template_file.fluentd-daemonset.rendered}"
  filename = "${var.data_dir}/fluentd-daemonset.yaml"
}
