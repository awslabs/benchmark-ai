FROM ubuntu:18.04

RUN apt update && apt install -y curl

COPY kitten.jpg /data/kitten.jpg
COPY run_benchmark.sh /benchmark/run_benchmark.sh

WORKDIR /benchmark
ENTRYPOINT ["./run_benchmark.sh"]