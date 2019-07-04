resource "aws_iam_role" "kube2iam-autoscaler-pod-role" {
  name = "bai-autoscaler-pod"
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
resource "aws_iam_role_policy" "kube2iam-autoscaler-pod-role-policy" {
  # Unfortunately it was not possible to make the autoscaler work with kube2iam without giving a specific role to the
  # autoscaler POD.
  # On the bright side, this is more secure since the autoscaler POD will only have the permissions it requires
  #
  # The policy was copied from https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/cloudprovider/aws
  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags",
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup",
          "autoscaling:UpdateAutoScalingGroup"
        ],
        "Resource": "*"
      }
    ]
  }
  EOF
  name = "autoscaling-actions"
  role = "${aws_iam_role.kube2iam-autoscaler-pod-role.name}"
}

data "template_file" "autoscaler_deployment" {
  template = "${file("${path.module}/template/cluster-autoscaler-autodiscover.tpl.yaml")}"

  vars = {
    eks_cluster_name   = "${module.eks.cluster_id}"
    cluster_region = "${var.region}"
    kube2iam_pod_role_name = "${aws_iam_role.kube2iam-autoscaler-pod-role.name}"
  }
}

resource "local_file" "update_autoscaler" {
  sensitive_content = "${data.template_file.autoscaler_deployment.rendered}"
  filename = "${var.data_dir}/autoscaler-deployment.yaml"
}
