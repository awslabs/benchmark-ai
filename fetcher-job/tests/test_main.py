from pytest import fixture

import bai_fetcher_job
from bai_fetcher_job.__main__ import main
from bai_fetcher_job.args import FetcherJobConfig


@fixture
def mock_retrying_fetch(mocker):
    return mocker.patch.object(bai_fetcher_job.__main__, "retrying_fetch", autospec=True)


@fixture
def mock_get_fetcher_job_args(mocker):
    return mocker.patch.object(bai_fetcher_job.__main__, "get_fetcher_job_args", autospec=True)


@fixture
def mock_config(mocker, mock_get_fetcher_job_args):
    mock_fetch_job_config = mocker.create_autospec(FetcherJobConfig)
    mock_get_fetcher_job_args.return_value = mock_fetch_job_config
    return mock_fetch_job_config


def test_main(mock_config, mock_retrying_fetch):
    main("--src=http://something.com/big.zip --dst=s3://somebucket/foo.zip")
    mock_retrying_fetch.assert_called_once_with(mock_config)
