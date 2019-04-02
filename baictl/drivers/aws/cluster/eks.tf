locals {
  # Check the section "The node.type label" at https://github.com/MXNetEdge/benchmark-ai/blob/master/docs/autoscaler-aws.md
  # for an explanation on each type of node.
  bai_worker_kubelet_args   = "--node-labels=node.type=bai-worker"
  k8s_services_kubelet_args  = "--node-labels=node.type=k8s-services"
  bai_services_kubelet_args = "--node-labels=node.type=bai-services"

  worker_groups = [
    {
      instance_type        = "t2.small"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = 2
      asg_max_size         = 10
      asg_min_size         = 1
      name                 = "k8s-services"
      kubelet_extra_args   = "${local.k8s_services_kubelet_args}"
    },
    {
      instance_type        = "m5d.4xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      asg_desired_capacity = 1
      asg_max_size         = 4
      asg_min_size         = 1
      name                 = "bai-services"
      kubelet_extra_args   = "${local.bai_services_kubelet_args}"
    },

    # bai-worker ASGs
    {
      instance_type        = "t2.small"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.t2.small"
    },
    {
      instance_type        = "t3.small"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.t3.small"
    },
    {
      instance_type        = "c5.large"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.c5.large"
    },
    {
      instance_type        = "c5.2xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.c5.2xlarge"
    },
    {
      instance_type        = "c5.4xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.c5.4xlarge"
    },
    {
      instance_type        = "c5.9xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.c5.9xlarge"
    },
    {
      instance_type        = "c5.18xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.c5.18xlarge"
    },
    {
      ami_id               = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
      instance_type        = "p3.2xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.p3.2xlarge"
    },
    {
      ami_id               = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
      instance_type        = "p3.8xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.p3.8xlarge"
    },
    {
      ami_id               = "${coalesce(var.eks_gpu_ami_id, data.aws_ami.eks-gpu-optimized.id)}"
      instance_type        = "p3.16xlarge"
      subnets              = "${join(",", module.vpc.private_subnets)}"
      name                 = "bai-worker.p3.16xlarge"
    }
  ]

  worker_groups_count = "12"

  worker_group_tags = {
    k8s-services = [
      {
        key = "k8s.io/cluster-autoscaler/node-template/label/node.type"
        value = "k8s-services"
        propagate_at_launch = true
      }
    ]
    bai-services = [
      {
        key = "k8s.io/cluster-autoscaler/node-template/label/node.type"
        value = "bai-services"
        propagate_at_launch = true
      }
    ]
    default = [
      {
        key = "k8s.io/cluster-autoscaler/node-template/label/node.type"
        value = "bai-worker"
        propagate_at_launch = true
      }
    ]
  }

  workers_group_defaults = {
    kubelet_extra_args   = "${local.bai_worker_kubelet_args}"
    ami_id               = "${coalesce(var.eks_cpu_ami_id, data.aws_ami.eks-cpu-optimized.id)}"
    key_name             = "${aws_key_pair.worker_key.key_name}"
    asg_min_size         = 0
    asg_desired_capacity = 0
    asg_max_size         = 3
    autoscaling_enabled  = true
  }
}

data "aws_ami" "eks-cpu-optimized" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amazon-eks-node-${var.k8s_version}-${var.eks_cpu_ami_version}"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["602401143452"] # AWS EKS account
}

data "aws_ami" "eks-gpu-optimized" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amazon-eks-gpu-node-${var.k8s_version}-${var.eks_gpu_ami_version}"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["602401143452"] # AWS EKS account
}

# Create a private key for each instance that will be a Kubernetes node so we can at least ssh into the box for
# troubleshooting.
resource "tls_private_key" "worker_private_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "worker_key" {
  key_name   = "worker_key"
  public_key = "${tls_private_key.worker_private_key.public_key_openssh}"
}

resource "local_file" "worker_privatekey_pem" {
  content  = "${tls_private_key.worker_private_key.private_key_pem}"
  filename = "worker_private.pem"
  provisioner "local-exec" {
    # HACK while Terraform does not have a proper way to set file permissions: https://github.com/terraform-providers/terraform-provider-local/issues/19
    command = "chmod 400 ${local_file.worker_privatekey_pem.filename}"
  }
}

module "eks" {
  source                               = "terraform-aws-modules/eks/aws"
  cluster_name                         = "${var.eks_cluster_name}"
  subnets                              = ["${module.vpc.private_subnets}"]
  tags                                 = "${local.tags}"
  vpc_id                               = "${module.vpc.vpc_id}"
  worker_groups                        = "${local.worker_groups}"
  worker_group_count                   = "${local.worker_groups_count}"
  worker_group_tags                    = "${local.worker_group_tags}"
  workers_group_defaults               = "${local.workers_group_defaults}"
  worker_additional_security_group_ids = ["${aws_security_group.all_worker_mgmt.id}"]
  map_roles                            = "${var.map_roles}"
  map_roles_count                      = "${var.map_roles_count}"
  map_users                            = "${var.map_users}"
  map_users_count                      = "${var.map_users_count}"
  map_accounts                         = "${var.map_accounts}"
  map_accounts_count                   = "${var.map_accounts_count}"
}
