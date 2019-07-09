from enum import Enum


class Strategy(Enum):
    SINGLE_NODE = "single_node"
    HOROVOD = "horovod"
