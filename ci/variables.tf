variable "projects" {
  type = list(string)
  default = [
    "client-lib",
    "metrics-pusher",
    "fetcher",
    "fetcher-job",
    "baictl",
    "kafka-utils",
    "puller",
    "executor",
    "watcher",
    "bff",
    "metrics-extractor",
    "prometheus-kafka-topic-exporter",
    "sm-executor",
    "cron-job"
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

variable "ci_docker_image" {
  type = map(string)
  default = {
    "default" = "benchmarkai/ci:kind"
    "bff"     = "gavin/bai-bff-dev"
  }
}

variable "ecr_repo" {
  type = map(string)
  default = {
    "bff" = "bai-bff"
  }
}

variable "github_organization" {
  type    = string
  default = "MXNetEdge"
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

variable "extra_users" {
  type    = string
  default = ""
}

variable "extra_roles" {
  type    = string
  default = ""
}
