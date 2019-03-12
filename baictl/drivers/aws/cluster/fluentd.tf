data "template_file" "fluentd-daemonset" {
  template = "${file("${path.module}/template/fluentd-daemonset.tpl.yaml")}"

  vars = {
    cluster_region      = "${var.region}"
    cluster_es_endpoint = "${aws_elasticsearch_domain.logs.endpoint}"
    cluster_log_bucket  = "${aws_s3_bucket.eks-logs-output.bucket}"
  }
}

resource "local_file" "fluentd-daemonset" {
  content  = "${data.template_file.fluentd-daemonset.rendered}"
  filename = "fluentd-daemonset.yaml"
}
