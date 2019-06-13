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
    "default" = "benchmarkai/ci"
    "bff"     = "gavin/bai-bff-dev"
  }
}

variable "ecr_repo" {
  type = map(string)
  default = {
    "bff" = "bai-bff"
  }
}
