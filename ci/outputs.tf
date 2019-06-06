output "ci-unit-tests-badge-url" {
  value = zipmap(
    aws_codebuild_project.ci-unit-tests.*.name,
    aws_codebuild_project.ci-unit-tests-master.*.badge_url,
  )
}

output "chime-hook-url-arn" {
  value = aws_secretsmanager_secret.secret-chime-hook-url.arn
}
