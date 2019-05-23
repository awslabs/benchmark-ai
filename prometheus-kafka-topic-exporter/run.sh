#!/bin/bash
set -ex

# Fill in template
sed  "s/@@KAFKA_BOOTSTRAP_SERVERS@@/$KAFKA_BOOTSTRAP_SERVERS/g" /config/kafka-topic-exporter.properties.template > /tmp/kafka-topic-exporter.properties

java -Dlog4j.configuration=file:///config/log4j.properties -jar /opt/kafka-topic-exporter.jar /tmp/kafka-topic-exporter.properties
