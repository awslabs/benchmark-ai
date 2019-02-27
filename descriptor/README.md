# Descriptor file

A descriptor file defines a benchmark job. This directory contains a template descriptor including explanatory comments on all fields. The descriptor is written in [TOML](https://github.com/toml-lang/toml).

The file is divided in the four following sections:

#### info
The fields in this section don't have any impact on the job to run, they contain merely informative data about the benchmark job.

#### hardware
The only choice users have at the moment is which kind of EC2 instance they want their code to run on.

#### env
Environment is defined by passing the Docker Hub user/repo:tag of the docker image containing the benchmark code.

#### ml
This section is for machine-learning related settings: code to run, dataset to use and parameters to pass in. It contains two subsections:

##### data
This subsection must specify the ID of the dataset used, as well as provide a script to download the data. 

##### params
This subsection is extracted from the descriptor file and passed on to the Python script running the benchmark (defined in ml.benchmark_code). Here, users can define the parameters their code will take.

#### output
Section for users to declare the metrics they will be tracking with this benchmark.


## Descriptor reader

A script is provided to parse descriptor files and generate the corresponding Kubernetes job configuration YAML file. To use the sript:

```
python descriptor_reader.py path_to_descriptor
```

