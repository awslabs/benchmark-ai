variable "region" {
}

variable "data_dir" {}

variable "prefix_list_ids" {
  type = "list"

  default = []
}

variable "ssh_access_cidr_blocks" {
  type    = "list"
  default = []
}

variable "cluster_name_prefix" {
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
  default     = "1.13"
}

variable "benchmark_workers_instance_types" {
  description = "The instance types that the EKS cluster can launch workers."
  type        = "list"
  default = [
    # Be mindful to the number of instance types that need to be supported because number of ASGs created is:
    #
    #     Number of availability zones * Number of instance types (this list)
    #
    # Given that the default limit is 200 ASG per region, this number can skyrocket easily.
    "t3.small",
    "c4.large",
    "c4.xlarge",
    "c4.8xlarge",
    "c5.2xlarge",
    "c5.18xlarge",
    "p2.xlarge",
    "p2.8xlarge",
    "p2.16xlarge",
    "p3.2xlarge",
    "p3.8xlarge",
    "p3.16xlarge",
    "p3dn.24xlarge"
  ]
}

variable "gpu_instance_type_prefixes" {
  type    = "list"
  default = ["p3", "p3dn", "p2", "g3", "g3s"]
}

##########################################################################################
# AMIs
##########################################################################################
variable "eks_cpu_ami_version" {
  description = "Version of the AMI used by the worker nodes. See https://github.com/awslabs/amazon-eks-ami/releases"
  default     = "v20190701"
}

variable "eks_gpu_ami_version" {
  description = "Version of the AMI used by the worker nodes. See https://github.com/awslabs/amazon-eks-ami/releases"
  default     = "v20190701"
}

variable "eks_cpu_ami_id" {
  description = "AMI id to launch workers that need CPU. Overrides the version specified by `eks_cpu_ami_version`."
  default     = "" # Empty because this must be a choice of the BAI administrator, wether he wants to override the AMI.
}

variable "eks_gpu_ami_id" {
  description = "AMI id to launch workers that need GPU. Overrides the version specified by `eks_gpu_ami_version`."
  default     = "" # Empty because this must be a choice of the BAI administrator, wether he wants to override the AMI.
}

variable "msk_brokers_per_az" {
  type    = "string"
  default = 1
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
