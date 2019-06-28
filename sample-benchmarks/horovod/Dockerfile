FROM horovod/horovod:0.16.4-tf1.14.0-torch1.1.0-mxnet1.4.1-py3.6

RUN mkdir -p /home/benchmark
COPY src/ /home/benchmark
WORKDIR /home/benchmark/
RUN pip3 install -r requirements.txt
RUN chmod +x train.sh

ENTRYPOINT ["/home/benchmark/train.sh"]
CMD []
