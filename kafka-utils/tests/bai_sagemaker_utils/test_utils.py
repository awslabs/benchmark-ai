from botocore.exceptions import ClientError

from bai_sagemaker_utils.utils import get_client_error_message, is_not_found_error

BAD_ERROR = ClientError({}, "operation")


def make_client_error(msg: str = "Something is wrong") -> ClientError:
    err = {"Error": {"Message": msg}}
    return ClientError(err, "operation")


def test_get_client_error_message():
    err = make_client_error(msg="some error")
    assert get_client_error_message(err) == "some error"


def test_bad_error_returns_default():
    assert get_client_error_message(BAD_ERROR) is None
    assert get_client_error_message(BAD_ERROR, default="default") == "default"


def test_is_not_found_error():
    not_found_error = make_client_error(msg="ThiS wAs nOt FoUnD")
    found_error = make_client_error(msg="Found")
    assert is_not_found_error(not_found_error) is True
    assert is_not_found_error(found_error) is False
