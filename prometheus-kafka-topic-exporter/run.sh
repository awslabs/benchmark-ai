#!/bin/bash
set -ex

# Fill in template - expects config to be mounted at /config/kafka-topic-exporter.properties
sed  "s/@@KAFKA_BOOTSTRAP_SERVERS@@/$KAFKA_BOOTSTRAP_SERVERS/g" /config/kafka-topic-exporter.properties.template > /tmp/kafka-topic-exporter.properties

# The default is to log to a local file - not that convenient when expecting output on stdout
java -Dlog4j.configuration=file:///config/log4j.properties -jar /opt/kafka-topic-exporter.jar /tmp/kafka-topic-exporter.properties
