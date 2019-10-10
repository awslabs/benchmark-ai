from botocore.exceptions import ClientError


def get_client_error_message(client_error: ClientError, default: str = None):
    return client_error.response.get("Error", {}).get("Message", default)


def is_not_found_error(client_error: ClientError):
    error_message = get_client_error_message(client_error, default="")
    return error_message.lower().find("not found") > 0
