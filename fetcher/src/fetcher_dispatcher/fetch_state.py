from bai_kafka_utils.utils import DEFAULT_ENCODING


class FetchState:
    STATE_RUNNING = "RUNNING".encode(DEFAULT_ENCODING)
    STATE_DONE = "DONE".encode(DEFAULT_ENCODING)
    STATE_FAILED = "FAILED".encode(DEFAULT_ENCODING)
