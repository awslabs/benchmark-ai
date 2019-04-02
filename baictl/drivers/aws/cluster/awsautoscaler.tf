data "template_file" "autoscaler_deployment" {
  template = "${file("${path.module}/template/cluster-autoscaler-autodiscover.tpl.yaml")}"

  vars = {
    cluster_name   = "${module.eks.cluster_id}-eks"
    cluster_region = "${var.region}"
  }
}

resource "local_file" "update_autoscaler" {
  content  = "${data.template_file.autoscaler_deployment.rendered}"
  filename = "autoscaler-deployment.yaml"
}
