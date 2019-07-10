# Metrics extractor 

This service runs in a container and listens to stderr/stdout (k8s log) of a container running in the same pod. 
Logs a read, parsed and pushed further to metrics pusher. The patterns and the names of the metric are configured 
in the toml descriptors of anubis jobs.

Read more [here](https://quip-amazon.com/kOX5AjZFabCk).

## Python dependencies

requirements.txt does not contain the required pip dependencies since they are managed through conda and are listed 
in environment.yml.
