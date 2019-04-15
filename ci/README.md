Contains all the files to set up the CI service for BAI.

To simplify things and have a CI up and running quickly, we're using [AWS CodeBuild](https://aws.amazon.com/codebuild/)
to run each build.

Using CodeBuild is temporary, we want evaluate other solutions in the future, probably using GoCD, or one of the open
platforms, like Travis, CircleCI, etc.

# Using these terraform files

- A GitHub token in the **environment variable** `$GITHUB_TOKEN` is required so that hooks can be created.


# Gotcha - Github MXNetEdge/benchmark-ai repo modeled in Terraform

To create the Github hooks the MXNetEdge/benchmark-ai repository is modeled in Terraform:

```hcl-terraform
resource "github_repository_webhook" "ci-unit-tests" {
  #...
}
```

The **gotcha** here is that it will try to create the MXNetEdge/benchmark-ai repo (or change its configurations), so
the first command to execute is:

```bash
terraform import github_repository.benchmark-ai benchmark-ai
```

# Gotcha - CodeBuild requires GitHub OAuth to be manually added

CodeBuild has a limitation where it is not possible to add the GitHub token via an API, that must be done
**for each region**.  

# Accounts

- **AWS account**: The account where the CodeBuild projects are created is 563267192464 (bai-gamma@amazon.com)
- **GitHub account**: A GitHub was not created yet. This is a TODO task.