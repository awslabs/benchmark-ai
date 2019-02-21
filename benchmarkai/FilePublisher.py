import sys

from .Publisher import Publisher


class FilePublisher(Publisher):
    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def publish(self, metrics_dict):
        for k, v in metrics_dict.items():
            self.stream.write(f'{str(k)}=v\n')
