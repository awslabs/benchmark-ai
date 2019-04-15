variable "projects" {
  type = "list"
  default = [
    "client-lib",
    "metrics-pusher",
    "fetcher",
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
