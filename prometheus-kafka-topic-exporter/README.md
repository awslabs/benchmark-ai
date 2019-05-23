TODO


make package
kubectl create configmap prometheus-kafka-topic-exporter-config --from-file config/

docker run -v /Users/mabreu/git_projects/benchmark-ai/prometheus-kafka-topic-exporter/config:/config:ro benchmarkai/prometheus-kafka-topic-exporter:d4f1303