output "cluster_endpoint" {
  description = "Endpoint for EKS control plane."
  value       = "${module.eks.cluster_endpoint}"
}

output "cluster_security_group_id" {
  description = "Security group ids attached to the cluster control plane."
  value       = "${module.eks.cluster_security_group_id}"
}

output "kubectl_config" {
  description = "kubectl config as generated by the module."
  value       = "${module.eks.kubeconfig}"
  sensitive   = true
}

output "config_map_aws_auth" {
  description = ""
  value       = "${module.eks.config_map_aws_auth}"
  sensitive   = true
}

output "region" {
  description = "AWS region."
  value       = "${var.region}"
}

output "availability_zones" {
  description = "AWS availability zones."
  value       = "${zipmap(data.aws_availability_zones.available.zone_ids, data.aws_availability_zones.available.names)}"
}

output "availability_zones_ids" {
  description = "AWS availability zones."
  value       = "${data.aws_availability_zones.available.zone_ids}"
}

output "eks_cluster_name" {
  description = "AWS EKS cluster name."
  value       = "${module.eks.cluster_id}"
}

output "bastion_public_ip" {
  value = "${aws_instance.bastion.public_ip}"
}

output "es_endpoint" {
  value = "${aws_elasticsearch_domain.logs.endpoint}"
}

output "bastion_pem_filename" {
  value     = "${local_file.bastion_privatekey_pem.filename}"
  sensitive = true
}

output "data_pull_s3" {
  description = "S3 bucket for data fetcher"
  value       = "${aws_s3_bucket.data-pull.id}"
}

output "scripts_exchange_s3" {
  description = "S3 bucket for BFF model code/scripts"
  value = "${aws_s3_bucket.scripts-exchange.id}"
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = ["${module.vpc.private_subnets}"]
}

output "msk_bootstrap_brokers" {
  description = "A list of brokers that a client application can use to bootstrap."
  value       = "${aws_msk_cluster.benchmark-msk-cluster.bootstrap_brokers}"
}

output "msk_zookeeper_connect" {
  description = "Connection string for Zookeeper."
  value       = "${aws_msk_cluster.benchmark-msk-cluster.zookeeper_connect_string}"
}

output "s3_endpoint" {
  description = "S3 Endpoint in the case of custome one. Empty if default"
  value       = ""
}

output "bff_security_group_id" {
  description = "Security group id to allow corp access to bff loadbalancer"
  value       = "${aws_security_group.bff_external_access.id}"
}

output "kube2iam_default_pod_role_name" {
  description = "Role that is used by PODs by default"
  value       = "${aws_iam_role.kube2iam-default-pod-role.name}"
}

output "sagemaker_role_name" {
  description = "SageMaker role name"
  value = "${aws_iam_role.sagemaker-role.name}"
}

output "sagemaker_output_s3" {
  description = "SageMaker role name"
  value = "${aws_s3_bucket.sagemaker-output.id}"
}

output "sagemaker_nodata_s3" {
  description = "SageMaker dummy data set"
  value = "s3://${aws_s3_bucket.data-pull.id}/${aws_s3_bucket_object.nodata.id}"
}
