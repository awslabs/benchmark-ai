# User defined metrics in CloudWatch

All metrics defined in the _output.metrics_ section of the [descriptor TOML file](executor/README.md) are automatically exported to AWS CloudWatch.
Accessing CloudWatch via the AWS console, they can be found in the _metrics_ section, under the namespace ANUBIS/METRICS 
(``https://console.aws.amazon.com/cloudwatch/home?region=<AWS_REGION>#metricsV2:graph=~();namespace=~'ANUBIS*2fMETRICS`` - 
substitute <AWS_REGION> with your region id, such as `us-east-1`, for example).

Metrics are labeled using:
 - _action-id_ of the benchmark run which produced them.
 - _client-id_ of the user who submitted the benchmark.
 - All **custom labels** defined in the _info.labels_ section of the descriptor file which defined the benchmark. 
 (see the [example descriptors](https://github.com/MXNetEdge/benchmark-ai/blob/master/executor/README.md#training) for reference)