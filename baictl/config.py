import yaml


class Config(object):
    _cfg = None

    def __init__(self, path):
        with open("config.yml", "r") as ymlfile:
            self._cfg = yaml.safe_load(ymlfile)

    def get_aws_prefix_lists(self):
        return self._cfg["aws_prefix_lists"]

    def get_aws_region(self):
        return self._cfg["aws_region"]
