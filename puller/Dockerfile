FROM       alpine:3.3

WORKDIR "/data"

RUN apk update && \
    apk add \
      libarchive-tools \
      bash \
      'python<3.0' \
      'py-pip<8.2' \
    && \
    rm -rf /var/cache/apk/*

RUN pip install awscli
# Replace busybox mini-tar with a smarter bsdtar+libarchive
RUN mv /bin/tar /bin/oldtar && ln -s $(which bsdtar) /bin/tar

COPY download-s3-files /opt/puller/download-s3-files

ENTRYPOINT ["/bin/bash", "/opt/puller/download-s3-files"]
CMD []
