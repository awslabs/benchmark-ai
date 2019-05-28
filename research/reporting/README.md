# Reporting Research

## Introduction

**Goal**: To figure out how to create the benchmark.ai report we receive via e-mail from elastic search.

**Approach**: Run the ELK stack locally in docker, pipe in some reasonable looking logs and try to query Elastic Search.

NOTE: the scripts here are not general purpose and pretty ad-hoc...don't judge me too harshly...

## Creating logs


First, get the ELK stack up:

```
$ docker run -d --name elk -p 5601:5601 -p 9200:9200 -p 5044:5044  sebp/elk
```

Be patient, it can take some time to come up.
Congratulation, you can now access Kibana on http://localhost:5601 and Elasticsearch on http://localhost:9200.

Then, we create the `report_cfg.yaml` file. This contains a list of benchmarks together with their labels and metrics. E.g.

```yaml
labels:
    Benchmark Desc: CIFAR-10
    Framework: MXNet
    Framework Desc: MKL/Symbol
    Instance Type: c5.18xlarge
    Model: ResNet-18
    Type: Training CV
  metrics:
    CPU Memory (mb): 2694.0
    Throughput (/s): 832.88
    Time to Train (s): 1504.2
    Top 1 Train Acc: 0.97
    Top 1 Val Acc: 0.79
    Uptime (s): 2026.6
  name: TrainingCV_benchmark_1
```

This metric configuration will be consumed used to generate the dummy logs.

To generate this file, run:

```
$ python3 extract_cfg.py
```

Now, generate an hour of dummy logs by running:

```
$ python3 generate_sample_data.py
```

Congratulations, you should now have some sample data to work off. The script generates 1 hour of data for each benchmark with 30 seconds intervals.


## Visualize

To see these logs:

1. Open [Kibana](http://localhost: 5601)
2. Go to the management tab, if you are not already there (the little cog)
3. Create Index pattern:
	1. if the dummy-metrics index pattern isn't shown, click on search for new data
	2. Index pattern: dummy-metrics, click next step
	3. Time filter field: @timestamp
	4. Click on create index pattern
4. Select the 'discover' tab (the little compass)

## Play around

You can play around with querying in the 'dev tools' tab.






