FROM openjdk:12.0.1-jdk-oraclelinux7

# exporter.port=12340 in kafka-topic-exporter.properties.template
EXPOSE 12340

RUN yum install -y wget
RUN wget -O /opt/kafka-topic-exporter.jar https://github.com/ogibayashi/kafka-topic-exporter/releases/download/v0.0.6/kafka-topic-exporter-0.0.6-jar-with-dependencies.jar
RUN wget -O /tmp/kafka_binary.tgz http://ftp-stud.hs-esslingen.de/pub/Mirrors/ftp.apache.org/dist/kafka/2.3.0/kafka_2.12-2.3.0.tgz && \
    mkdir /opt/kafka && \
    tar -xzf /tmp/kafka_binary.tgz --strip 1 -C /opt/kafka && \
    rm /tmp/kafka_binary.tgz

ADD run.sh /opt/run.sh

# Config has to be mounted at /config
ENTRYPOINT [ "/bin/bash", "-c" ]
CMD [ "/opt/run.sh" ]