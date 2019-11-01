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
