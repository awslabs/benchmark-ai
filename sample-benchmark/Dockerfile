FROM mxnet/python
RUN apt-get install unzip
RUN pip install benchmarkai-client-lib
RUN mkdir /home/benchmark
COPY benchmark/ /home/benchmark
WORKDIR /home/benchmark/
