import benchmarkai as bai

bai.emit({"foo": "bar"})
bai.emit({bai.Metrics("foo", "one"): "bar"})
