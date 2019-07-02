class UnRetryableError(Exception):
    pass


class RetryableError(Exception):
    pass


class InvalidDigestError(UnRetryableError):
    pass


class HttpClientError(UnRetryableError):
    pass


class HttpServerError(RetryableError):
    pass


# Unretryable since boto retries on it's own
# TODO - Align retry policies between boto3 and us
class S3Error(UnRetryableError):
    pass


# Any curl exceptions that was before HTTP was properly established.
# DNS is mostly unretryable.
# Cannot connect - probably is.
# TODO - investigate later
class CurlError(UnRetryableError):
    pass
