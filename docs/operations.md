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
This document contains some tips on how to operate the Benchmark AI system.

# SSH

The terraform modules will create a very handy file named `ssh-config` at the `bai` directory:

```
# SSH into bastion
ssh -F bai/ssh-config bastion

# SSH into an EKS worker
ssh -F bai/ssh-config <IP of worker | DNS of worker>
```

# Tunnel for Elasticsearch + Kibana

```
ssh -F bai/ssh-config estunnel -N
```

Now you can access Kibana by visiting: https://localhost:9200/_plugin/kibana


# Inside an EKS worker

After SSHing into the EKS instance you are interested in:

## Kubelet logs

```
sudo journalctl -u kubelet
```