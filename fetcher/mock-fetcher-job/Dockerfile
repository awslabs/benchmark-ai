FROM zookeeper:3.4.14

COPY mock-fetcher-job /opt/fetcher/mock-fetcher-job
RUN chmod +x /opt/fetcher/mock-fetcher-job

ENTRYPOINT ["/opt/fetcher/mock-fetcher-job"]
