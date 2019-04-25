output "ci-unit-tests-badge-url" {
  value = "${zipmap(aws_codebuild_project.ci-unit-tests.*.name, aws_codebuild_project.ci-unit-tests-master.*.badge_url)}"
}
