resource "aws_ecr_repository" "ecr" {
  count = length(var.projects)
  name = var.projects[count.index]
}
