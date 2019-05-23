# Prometheus Kafka Topic Exporter
This services establishes the bridge between Kafka topics and Prometheus. It subscribes to the BAI_METRICS topic
to listen for metrics that have been published. They will then be available at 0.0.0.0:12340/metrics to be
scraped by Prometheus.


## Format
The messages submitted to the topic have to be in the following format:
```
{
  "name": "<metric_name>",
  "value": <metric_value>,
  "timestamp": <epoch_value_with_millis>,
  "labels: {
    "foolabel": "foolabelvalue",
    "barlabel": "barlabelvalue"
  }
}
```
which will lead to the following metric to be exported:
```
<kafka_topic_name>_<metric_name>{foolabel="foolabelvalue", barlabel="barlabelvalue"} <metric_value> <epoch_value>
```
Source: https://github.com/ogibayashi/kafka-topic-exporter


## Debug commands
These commands have been useful during the development - disregard them.
```
make package
kubectl create configmap prometheus-kafka-topic-exporter-config --from-file config/
docker run -v /Users/mabreu/git_projects/benchmark-ai/prometheus-kafka-topic-exporter/config:/config:ro benchmarkai/prometheus-kafka-topic-exporter:d4f1303

kubectl scale deployment prometheus-kafka-topic-exporter --replicas=0 && kubectl scale deployment prometheus-kafka-topic-exporter --replicas=1

ssh -F ~/.bai/ssh-config bastion
apt install -y default-jre
bin/kafka-topics.sh --list --bootstrap-server b-1.benchmark-cluster.pceosy.c2.kafka.us-west-2.amazonaws.com:9092
kubectl describe configmap outputs-infrastructure -> msk_zookeeper_connect
/snap/bin/kafka.topics --create --if-not-exists --zookeeper 172.16.45.112:2181 --replication-factor 3 --partitions 1 --topic MARCO_TEST
bin/kafka-console-producer.sh --broker-list b-1.benchmark-cluster.pceosy.c2.kafka.us-west-2.amazonaws.com:9092 --topic MARCO_TEST
        {"window":{"start":"2018-07-25T12:50:30.000Z","end":"2018-07-25T12:51:00.000Z"},"labels":{"port":"AMS","hostname":"963_P2_CLU","peak":"L4","channel":"23","transactionstatus":"OK"},"value":"1","name":"queries_sum"}
bin/kafka-console-consumer.sh --bootstrap-server b-1.benchmark-cluster.pceosy.c2.kafka.us-west-2.amazonaws.com:9092 --topic MARCO_TEST --from-beginning

kubectl port-forward prometheus-kafka-topic-exporter-57f8fd9f8c-pvlbb 12340 12340
Go to 127.0.0.1/metrics
Produces

>   # HELP MARCO_TEST_queries_sum
>   # TYPE MARCO_TEST_queries_sum gauge
>   MARCO_TEST_queries_sum{port="AMS",hostname="963_P2_CLU",peak="L4",channel="23",transactionstatus="OK",} 1.0

```
