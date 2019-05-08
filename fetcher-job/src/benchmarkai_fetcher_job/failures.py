class UnRetryableError(Exception):
    pass


class RetryableError(Exception):
    pass


class InvalidDigestException(UnRetryableError):
    pass


class HttpClientError(UnRetryableError):
    pass


class HttpServerError(RetryableError):
    pass
