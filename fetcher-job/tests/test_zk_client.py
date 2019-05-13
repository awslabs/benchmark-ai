from kazoo.client import KazooClient
from unittest.mock import patch, create_autospec

from benchmarkai_fetcher_job import zk_client
from benchmarkai_fetcher_job.states import FetcherStatus, FetcherResult
from benchmarkai_fetcher_job.zk_client import update_zk_node

FETCHER_RESULT = FetcherResult(FetcherStatus.DONE, "Success")
ZK_NODE_PATH = "/zk/path"
ZK_ENSEMBLE = "Z1"


@patch.object(zk_client, "KazooClient")
def test_update_zk_node(mockKazooClient):
    mock_zk_client = mockKazooClient.return_value = create_autospec(KazooClient)

    update_zk_node(ZK_NODE_PATH, ZK_ENSEMBLE, FETCHER_RESULT)

    mockKazooClient.assert_called_with(hosts=ZK_ENSEMBLE)

    mock_zk_client.start.assert_called_once()
    mock_zk_client.set.assert_called_with(ZK_NODE_PATH, FETCHER_RESULT.to_binary())
    mock_zk_client.stop.assert_called_once()
