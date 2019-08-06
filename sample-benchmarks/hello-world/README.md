# Anubis Hello world

This directory contains a basic Hello world example benchmark for Anubis. To run it, use:

```shell
anubis --submit descriptor.toml
```



## Script mode example

Besides the basic usage described above, this example also shows how to use Anubis' script mode. 
This mode lets you submit files (or directories) along with your descriptor. 
For example, the command below submits the src/ directory: 

```shell
anubis --submit descriptor-script-mode.toml --script src
```

Inside the container executing your benchmark, scripts submitted using the --script option will be located in the
BAI_SCRIPTS_PATH directory (the BAI_SCRIPTS_PATH environment variable is automatically set by Anubis in the container 
where your code runs). In this example, `src/` will be at `BAI_SCRIPTS_PATH/src/`.