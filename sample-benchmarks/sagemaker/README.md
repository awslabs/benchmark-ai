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
# Sagemaker benchmark example

This directory contains the descriptor file (horovod.toml) for an example benchmark which uses Sagemaker as execution engine.

The code run by this example can be found at [Horovod's GitHub](https://github.com/horovod/horovod/blob/master/examples/tensorflow_synthetic_benchmark.py).

```shell
git clone https://github.com/horovod/horovod.git

anubis --submit horovod.toml --script <PATH-TO-SOURCES>/horovod
```