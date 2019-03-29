variable "region" {
  default = "eu-west-1"
}

variable "prefix_list_ids" {
  type        = "list"

  default = []
}

variable "cluster_name" {
  type    = "string"
  default = "benchmark-cluster"
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

variable "eks_ami_version" {
  description = "Version of the AMI used by the worker nodes. See https://github.com/awslabs/amazon-eks-ami"
  default = "v20190327"
}

variable "eks_cpu_ami_id" {
  description = "AMI id to launch workers that need CPU"
  # TODO: This value should be empty, but EKS broke the CPU version of v20190327 - https://github.com/awslabs/amazon-eks-ami/issues/233
  default = "ami-0eeeef929db40543c"
}

variable "eks_gpu_ami_id" {
  description = "AMI id to launch workers that need GPU"
  default = ""
}
