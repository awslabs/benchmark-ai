FROM       alpine:3.3

WORKDIR "/data"

RUN apk update && \
    apk add \
      bash \
      'python<3.0' \
      'py-pip<8.2' \
    && \
    rm -rf /var/cache/apk/*

RUN pip install awscli

ADD download-s3-files /opt/puller/download-s3-files

ENTRYPOINT ["/bin/bash", "/opt/puller/download-s3-files"]
CMD []
