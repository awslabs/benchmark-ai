from unittest.mock import patch

# Regression test
from fetcher_dispatcher import fetcher_dispatcher


@patch.object(fetcher_dispatcher, "create_fetcher_dispatcher")
def test_main(mock_create_fetcher_dispatcher):
    from fetcher_dispatcher.__main__ import main
    main("--consumer-topic IN "
         "--producer-topic OUT "
         "--s3-data-set-bucket S3 "
         "--bootstrap-servers K1,K2 "
         "--kubeconfig /path/cfg")
