# Sagemaker benchmark example

This directory contains the descriptor file (horovod.toml) for an example benchmark which uses Sagemaker as execution engine.

The code run by this example can be found at [Horovod's GitHub](https://github.com/horovod/horovod/blob/master/examples/tensorflow_synthetic_benchmark.py).

```shell
git clone https://github.com/horovod/horovod.git

anubis --submit horovod.toml --script <PATH-TO-SOURCES>/horovod
```