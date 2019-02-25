data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

resource "aws_iam_service_linked_role" "default" {
  aws_service_name = "es.amazonaws.com"
  description      = "AWSServiceRoleForAmazonElasticsearchService Service-Linked Role"
}
resource "aws_elasticsearch_domain" "logs" {
  domain_name           = "logs"
  elasticsearch_version = "6.4"

  vpc_options {
    subnet_ids = ["${module.vpc.private_subnets[0]}"]
    security_group_ids = ["${module.eks.worker_security_group_id}"]
  }

  ebs_options{
      ebs_enabled = true
      volume_size = 16
  }

    access_policies = <<CONFIG
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "es:ESHttpDelete",
                "es:ESHttpGet",
                "es:ESHttpHead",
                "es:ESHttpPost",
                "es:ESHttpPut"
            ],
            "Principal": {
            "AWS": ["*"]
            },
            "Effect": "Allow",
            "Resource": "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/logs/*"
        }
    ]
}
CONFIG

depends_on = ["aws_iam_service_linked_role.default"]

}

