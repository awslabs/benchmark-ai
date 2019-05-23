TODO


make package
kubectl create configmap prometheus-kafka-topic-exporter-config --from-file config/

docker run -v /Users/mabreu/git_projects/benchmark-ai/prometheus-kafka-topic-exporter/config:/config:ro benchmarkai/prometheus-kafka-topic-exporter:d4f1303



kubectl scale deployment prometheus-kafka-topic-exporter --replicas=0 && kubectl scale deployment prometheus-kafka-topic-exporter --replicas=1



ssh -F ~/.bai/ssh-config bastion
apt install -y default-jre
bin/kafka-topics.sh --list --bootstrap-server b-1.benchmark-cluster.pceosy.c2.kafka.us-west-2.amazonaws.com:9092
kubectl describe configmap outputs-infrastructure -> msk_zookeeper_connect
/snap/bin/kafka.topics --create --if-not-exists --zookeeper 172.16.45.112:2181 --replication-factor 3 --partitions 1 --topic export.blabla
bin/kafka-console-producer.sh --broker-list b-1.benchmark-cluster.pceosy.c2.kafka.us-west-2.amazonaws.com:9092 --topic export.blabla
bin/kafka-console-consumer.sh --bootstrap-server b-1.benchmark-cluster.pceosy.c2.kafka.us-west-2.amazonaws.com:9092 --topic export.blaba --from-beginning