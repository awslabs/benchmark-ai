FROM python:3-alpine

RUN mkdir -p /home/benchmark
COPY src/ /home/benchmark
WORKDIR /home/benchmark/
RUN pip3 install -r requirements.txt

CMD ["python3", "hello-world.py"]
