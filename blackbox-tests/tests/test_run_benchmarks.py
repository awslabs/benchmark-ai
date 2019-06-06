from bai_client.client import BaiClient


def test_hello_world():
    client = BaiClient()
    ret = client.submit(
        "/home/ANT.AMAZON.COM/muenze/Projects/benchmark-ai/sample-benchmarks/hello-world/descriptor.toml"
    )
    print(ret)
