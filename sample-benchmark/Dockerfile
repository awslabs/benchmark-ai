FROM mxnet/python
RUN mkdir /home/benchmark
COPY benchmark/ /home/benchmark
WORKDIR /home/benchmark/

CMD ["python", "image_classification.py", "--model=resnet50_v2" ]