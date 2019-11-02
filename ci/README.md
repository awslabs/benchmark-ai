<!---
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
-->
Contains all the files to set up the CI service for BAI.

To simplify things and have a CI up and running quickly, we're using [AWS CodeBuild](https://aws.amazon.com/codebuild/)
to run each build.

Using CodeBuild is temporary, we want evaluate other solutions in the future, probably using GoCD, or one of the open
platforms, like Travis, CircleCI, etc.

# Gotcha - CodeBuild requires GitHub OAuth to be manually added

CodeBuild has a limitation where it is not possible to add the GitHub token via an API, that must be done
**for each region**.  

# Accounts

- **AWS account**: The account where the CodeBuild projects are created is 563267192464 (bai-gamma@amazon.com)
- **GitHub account**: A GitHub was not created yet. This is a TODO task.