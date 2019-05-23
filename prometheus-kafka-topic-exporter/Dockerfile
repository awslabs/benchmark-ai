FROM openjdk:12.0.1-jdk-oraclelinux7

RUN yum install -y wget
RUN wget -O /opt/kafka-topic-exporter.jar https://github.com/ogibayashi/kafka-topic-exporter/releases/download/v0.0.6/kafka-topic-exporter-0.0.6-jar-with-dependencies.jar

ADD run.sh /opt/run.sh

# Config has to be mounted at /config

ENTRYPOINT [ "/bin/bash", "-c" ]
CMD [ "/opt/run.sh" ]