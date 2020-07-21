variable "projects" {
  type = list(string)
  default = [
    "client-lib",
    "blackbox-tests",
    "metrics-pusher",
    "fetcher",
    "fetcher-job",
    "baictl",
    "kafka-utils",
    "puller",
    "executor",
    "watcher",
    "bai-bff",
    "metrics-extractor",
    "prometheus-kafka-topic-exporter",
    "sm-executor",
    "anubis-cron-job",
    "job-status-trigger",
    "cloudwatch-exporter"
  ]
}

variable "github_token" {
  type    = string
  default = ""
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "bootstrap_docker_image_tag" {
  type    = string
  default = "bootstrap-image:latest"
}

variable "github_organization" {
  type    = string
  default = "awslabs"
}

variable "github_branch" {
  type    = string
  default = "master"
}

variable "chime_hook_url" {
  type    = string
  default = ""
}

variable "run_integration_tests" {
  type    = bool
  default = true
}

variable "prefix_list_id" {
  type = string
}

variable "white_listed_cidr_blocks" {
  type = string
}

variable "extra_users" {
  type    = string
  default = ""
}

variable "extra_roles" {
  type    = string
  default = ""
}
