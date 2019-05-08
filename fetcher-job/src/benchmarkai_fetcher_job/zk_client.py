from kazoo.client import KazooClient

from benchmarkai_fetcher_job.states import FetcherResult


def update_zk_node(zk_node_path: str, zookeeper_ensemble: str, state: FetcherResult):
    zk = KazooClient(hosts=zookeeper_ensemble)
    zk.start()
    zk.set(zk_node_path, state.to_binary())
    zk.stop()
