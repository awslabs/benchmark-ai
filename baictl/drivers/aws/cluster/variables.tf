variable "region" {
  default = "eu-west-1"
}

variable "prefix_list_ids" {
  type        = "list"

  default = []
}

variable "eks_cluster_name" {
  type    = "string"
  default = "benchmark-eks-cluster"
}

variable "map_accounts" {
  description = "Additional AWS account numbers to add to the aws-auth configmap."
  type        = "list"

  default = []
}

variable "map_accounts_count" {
  description = "The count of accounts in the map_accounts list."
  type        = "string"
  default     = 0
}

variable "map_roles" {
  description = "Additional IAM roles to add to the aws-auth configmap."
  type        = "list"

  default = []
}

variable "map_roles_count" {
  description = "The count of roles in the map_roles list."
  type        = "string"
  default     = 0
}

variable "map_users" {
  description = "Additional IAM users to add to the aws-auth configmap."
  type        = "list"

  default = []
}

variable "map_users_count" {
  description = "The count of roles in the map_users list."
  type        = "string"
  default     = 0
}

variable "k8s_version" {
  description = "Version of Kubernetes"
  default = "1.11"
}

##########################################################################################
# AMIs
##########################################################################################
variable "eks_cpu_ami_version" {
  description = "Version of the AMI used by the worker nodes. See https://github.com/awslabs/amazon-eks-ami"
  default = "v20190329"
}

variable "eks_gpu_ami_version" {
  description = "Version of the AMI used by the worker nodes. See https://github.com/awslabs/amazon-eks-ami"
  default = "v20190327"
}

variable "eks_cpu_ami_id" {
  description = "AMI id to launch workers that need CPU. Overrides the version specified by `eks_cpu_ami_version`."
  default = "" # Empty because this must be a choice of the BAI administrator, wether he wants to override the AMI.
}

variable "eks_gpu_ami_id" {
  description = "AMI id to launch workers that need GPU. Overrides the version specified by `eks_gpu_ami_version`."
  default = "" # Empty because this must be a choice of the BAI administrator, wether he wants to override the AMI.
}
variable "msk_cluster_name" {
  type    = "string"
  default = "benchmark-msk-cluster"
}

variable "msk_broker_count" {
  type    = "string"
  default = 3
}

variable "msk_broker_instance_type" {
  type    = "string"
  default = "kafka.m5.large"
}

variable "msk_broker_volume_size" {
  type    = "string"
  default = "1000"
}

variable "msk_kafka_version" {
  type    = "string"
  default = "2.1.0"
}
