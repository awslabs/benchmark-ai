from pytest import fixture


from bai_kafka_utils.events import BenchmarkEvent


@fixture
def benchmark_event():
    return BenchmarkEvent(
        action_id="ACTION_ID",
        message_id="MESSAGE_ID",
        client_id="CLIENT_ID",
        client_version="DONTCARE",
        client_username="DONTCARE",
        authenticated=False,
        tstamp=1556814924121,
        visited=[],
        type="DONTCARE",
        payload=None,
        parent_action_id="",
    )
