variable "projects" {
  type = "list"
  default = [
    "client-lib",
    "metrics-pusher",
    "fetcher",
    "fetcher-job",
    "baictl",
    "kafka-utils",
    "puller",
    "reports",
    "executor",
    "watcher",
  ]
}

variable "github_token" {
  type = "string"
  default = ""
}

variable "region" {
  type = "string"
  default = "us-east-1"
}

variable "ci_docker_image" {
  type = "string"
  default = "jlcont/bai-ci-python:260419"
}
