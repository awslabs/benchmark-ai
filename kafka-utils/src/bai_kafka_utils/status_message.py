from bai_kafka_utils.events import StatusMessageBenchmarkEvent, BenchmarkEvent, StatusMessagePayload


def create_status_message_event(event: BenchmarkEvent, msg: str) -> StatusMessageBenchmarkEvent:
    return StatusMessageBenchmarkEvent(
        action_id=event.action_id,
        client_id=event.client_id,
        message_id=event.message_id,
        client_username=event.client_username,
        client_version=event.client_version,
        authenticated=event.authenticated,
        tstamp=event.tstamp,
        payload=StatusMessagePayload(msg),
        visited = []
    )



