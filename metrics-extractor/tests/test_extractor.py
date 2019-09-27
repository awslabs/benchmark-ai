#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from unittest.mock import ANY, MagicMock

import kubernetes
import kubernetes.watch
import pytest
from kubernetes.client.rest import ApiException
from mock import call

from anubis_metrics_extractor import log_listener
from anubis_metrics_extractor.log_listener import (
    EnvironmentReader,
    LogExtractor,
    LogExtractorOptions,
    Metric,
    MAX_ATTEMPTS,
)

patterns = dict(
    one="Lio=",  # .*
    another="Lis=",  # .+
    invalid="Ww==",  # [
    accuracy="YWNjdXJhY3k9KFstK10/XGQqXC5cZCt8XGQrKQ==",  # accuracy=([-+]?\d*\.\d+|\d+)
)


@pytest.fixture
def default_options():
    reader = EnvironmentReader(
        '[{{"name": "mama", "pattern": "{}", "units": ""}}, {{"name": "papa", "pattern": "{}", "units": ""}}]'.format(
            patterns["one"], patterns["another"]
        )
    )
    metrics = reader.get_metrics()
    return LogExtractorOptions(
        pod_name="pod_name", pod_namespace="pod_namespace", pod_container="pod_container", metrics=metrics
    )


@pytest.fixture
def real_options():
    reader = EnvironmentReader('{{"name": "accuracy", "pattern": "{}", "units": ""}}'.format(patterns["accuracy"]))
    metrics = reader.get_metrics()
    return LogExtractorOptions(
        pod_name="pod_name", pod_namespace="pod_namespace", pod_container="pod_container", metrics=metrics
    )


@pytest.fixture
def client_mock(mocker):
    return mocker.patch.object(log_listener, "client", autospec=True)


@pytest.fixture
def api_mock(mocker, client_mock):
    mock = mocker.create_autospec(kubernetes.client.CoreV1Api)
    client_mock.CoreV1Api.return_value = mock
    return mock


@pytest.fixture
def stream_mock(api_mock):
    mock = MagicMock()
    mock.stream.return_value = iter(
        [b"lalala", b"accuracy=20.34", b"dududu", b"accuracy=0.35, something something, accuracy=0.88"]
    )
    api_mock.read_namespaced_pod_log.return_value = mock
    return mock


@pytest.fixture
def stream_one_api_exception_mock(api_mock):
    mock = MagicMock()
    mock.stream.return_value = iter(
        [b"lalala", b"accuracy=20.34", b"dududu", b"accuracy=0.35, something something, accuracy=0.88"]
    )
    api_mock.read_namespaced_pod_log.side_effect = [ApiException(status=400, reason="Not there yet"), mock]
    return mock


@pytest.fixture
def stream_only_api_exceptions_mock(api_mock):
    mock = MagicMock()
    api_mock.read_namespaced_pod_log.side_effect = [ApiException(status=400, reason="Not there yet")] * MAX_ATTEMPTS
    return mock


@pytest.fixture
def pusher_mock(mocker):
    return mocker.patch.object(log_listener, "emit", autospec=True)


# ----- tests -----


def test_construction(default_options):
    extractor = LogExtractor(default_options)
    assert len(extractor.metrics) == 2


def test_empty(default_options):
    options = default_options
    options.metrics = []
    extractor = LogExtractor(options)
    assert len(extractor.metrics) == 0


def test_invalid(default_options):
    options = default_options
    options.metrics = [Metric(name="name", pattern=patterns["invalid"], units="")]
    with pytest.raises(re.error):
        _ = LogExtractor(options)


def test_stream_with_container(default_options, client_mock, api_mock):
    extractor = LogExtractor(default_options)
    extractor.listen()
    client_mock.CoreV1Api.assert_called_once()
    api_mock.read_namespaced_pod_log.assert_called_once_with(
        _preload_content=ANY, container="pod_container", follow=True, name="pod_name", namespace="pod_namespace"
    )


def test_stream_no_container(default_options, client_mock, api_mock):
    options = default_options
    options.pod_container = None
    extractor = LogExtractor(options)
    extractor.listen()
    client_mock.CoreV1Api.assert_called_once()
    api_mock.read_namespaced_pod_log.assert_called_once_with(
        _preload_content=ANY, follow=True, name="pod_name", namespace="pod_namespace"
    )


# full test


def test_stream(real_options, client_mock, api_mock, stream_mock, pusher_mock):
    extractor = LogExtractor(real_options)
    extractor.listen()
    client_mock.CoreV1Api.assert_called_once()
    api_mock.read_namespaced_pod_log.assert_called_once()
    calls = [call({"accuracy": "20.34"}), call({"accuracy": "0.35"}), call({"accuracy": "0.88"})]
    pusher_mock.assert_has_calls(calls)


def test_stream_recovers_from_error(
    real_options, client_mock, api_mock, stream_one_api_exception_mock, pusher_mock, mocker
):
    mock_time = mocker.patch("time.sleep")
    extractor = LogExtractor(real_options)
    extractor.listen()
    client_mock.CoreV1Api.assert_called_once()
    assert api_mock.read_namespaced_pod_log.call_count == 2
    calls = [call({"accuracy": "20.34"}), call({"accuracy": "0.35"}), call({"accuracy": "0.88"})]
    pusher_mock.assert_has_calls(calls)
    assert mock_time.call_count == 1


def test_stream_raise_after_max_retries_errors(
    mocker, real_options, client_mock, api_mock, stream_only_api_exceptions_mock, pusher_mock
):
    mock_time = mocker.patch("time.sleep")
    extractor = LogExtractor(real_options)
    with pytest.raises(RuntimeError):
        extractor.listen()
    client_mock.CoreV1Api.assert_called_once()
    assert api_mock.read_namespaced_pod_log.call_count == MAX_ATTEMPTS
    assert mock_time.call_count == MAX_ATTEMPTS
