from bai_client.client import _convert_status_json_response


def test_convert_status_json_response(datadir):
    s = (datadir / "status_event.json").read_text("utf-8")
    event = _convert_status_json_response(s)
    print(event)
