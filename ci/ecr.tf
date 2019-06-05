resource "aws_ecr_repository" "ecr" {
  count = length(var.projects)
  name = lookup(var.ecr_repo, var.projects[count.index], var.projects[count.index])
}
