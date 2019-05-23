FROM openjdk:12.0.1-jdk-oraclelinux7

RUN yum install -y wget
RUN wget -O /opt/kafka-topic-exporter.jar https://github.com/ogibayashi/kafka-topic-exporter/releases/download/v0.0.6/kafka-topic-exporter-0.0.6-jar-with-dependencies.jar

# The default is to log to a local file - not that convenient when expecting output on stdout
ADD prometheus-kafka-topic-exporter/config/log4j.properties /opt/log4j.properties

ENTRYPOINT [ "/bin/bash", "-c" ]

# Expect config to be mounted at /config/kafka-topic-exporter.properties
CMD [ "java -Dlog4j.configuration=file:///opt/log4j.properties -jar /opt/kafka-topic-exporter.jar /config/kafka-topic-exporter.properties" ]
