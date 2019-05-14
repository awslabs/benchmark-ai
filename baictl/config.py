import yaml


class Config(object):
    """
    Config object for baictl
    """

    _cfg = None

    def __init__(self, path):
        with open(path, "r") as ymlfile:
            self._cfg = yaml.safe_load(ymlfile)

    def get_aws_prefix_lists(self):
        return self._cfg["aws_prefix_lists"]

    def get_aws_region(self):
        return self._cfg["aws_region"]
