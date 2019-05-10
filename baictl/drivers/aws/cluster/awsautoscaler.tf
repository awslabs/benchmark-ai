data "template_file" "autoscaler_deployment" {
  template = "${file("${path.module}/template/cluster-autoscaler-autodiscover.tpl.yaml")}"

  vars = {
    eks_cluster_name   = "${module.eks.cluster_id}"
    cluster_region = "${var.region}"
  }
}

resource "local_file" "update_autoscaler" {
  sensitive_content = "${data.template_file.autoscaler_deployment.rendered}"
  filename = "${var.data_dir}/autoscaler-deployment.yaml"
}
