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
# Anubis Hello world

This directory contains a basic Hello world example benchmark for Anubis. To run it, use:

```shell
anubis --submit descriptor.toml
```



## Script mode example

Besides the basic usage described above, this example also shows how to use Anubis' script mode.
This mode lets you submit your script file, or the encompassing top level directory of the files you wish to post, along with your descriptor.
For example, the command below submits the src/ directory:

```shell
anubis --submit descriptor-script-mode.toml --script src
```

Inside the container executing your benchmark, scripts submitted using the --script option will be located in the
BAI_SCRIPTS_PATH directory (the BAI_SCRIPTS_PATH environment variable is automatically set by Anubis in the container
where your code runs). In this example, `src/` will be at `BAI_SCRIPTS_PATH/src/`.

### Additional flags

In both scenarios the additional augmenting arguments can be provided to the [anubis](bai-bff/bin/anubis) command to provide additional feedback semantics.<br>

``` shell
--force --verbose --debug --tail --watch
```

If you wish to submit your job and see the status feedback right way and continue to watch them as they arrive update your command line like this.<br>

``` shell
anubis --watch --status --submit descriptor-script-mode.toml --script src
```
(order does not matter)

See: [anubis starter doc](/bai-bff/docs/anubis-client.md) and --help for more information.
