import benchmarkai as bai

bai.emit({"alexnet.batchsize1.latency": 12})
bai.emit({bai.Metrics("alexnet.batchsize1.latency", "ms"): 12})
bai.emit({bai.Metrics("resnet152.batchsize256.throughput", "items_per_second"): 240})
