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
This project is meant to contain blackbox tests for BAI

### Can I run black box tests locally?
Yes. Just pass the bff endpoint to pytest either with an arg **--bff-endpoint** or an env variable **BFF_ENDPOINT**

You can get it through anubis.
```shell
anubis --show-registered-service-endpoint
```
An alternative is to request the endpoint through kubectl.
```shell
export BFF_ENDPOINT=http://$(kubectl get service bai-bff -o jsonpath='{.status.loadBalancer.ingress[*].hostname}')
```

After that you can run blackbox tests locally or from your IDE.