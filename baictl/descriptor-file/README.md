# Descriptor file

A descriptor file defines a benchmark job. This directory contains a template descriptor including explanatory comments on all fields. The descriptor is written in [TOML](https://github.com/toml-lang/toml).

The file is divided in the six following sections:

#### info
The fields in this section don't have any impact on the job to run, they contain merely informative data about the benchmark job.

#### hardware
The only choice users have at the moment is which kind of EC2 instance they want their code to run on.

#### env
Environment is defined by passing the Docker Hub user/repo:tag of the docker image containing the benchmark code.

#### ml
This section is for machine-learning related settings: code to run, dataset to use and parameters to pass in. It contains two subsections:

##### params
This subsection is extracted from the descriptor file and passed on to the Python script running the benchmark (defined in ml.benchmark_code). Here, users can define the parameters their code will take.

#### data
This section must specify the ID of the dataset used. For any required data source, users can provide a download script, a preprocessing command and the path where the resulting data should be located in the container filesystem for the benchmark script to use it.

#### output
Section for users to declare the metrics they will be tracking with this benchmark.


## Descriptor reader

The descriptor_reader Python script is provided to parse descriptor files and generate the corresponding Kubernetes job configuration YAML file. It is called as follows:

```
python descriptor_reader.py path_to_descriptor.toml
```

This utility is used by the baictl CLI to run Kubernetes jobs.
