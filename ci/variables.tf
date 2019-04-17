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
