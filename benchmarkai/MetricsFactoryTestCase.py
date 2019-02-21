import unittest
from unittest import mock

import benchmarkai


class MetricsFactoryTestCase(unittest.TestCase):
    def setUp(self):
        self.metricsFactory = benchmarkai.MetricsFactory()
        self.publisher = unittest.mock.Mock()

    def test_register_publisher(self):
        self.metricsFactory.register_publisher(self.publisher)
        data = {}
        self.metricsFactory.emit(data)
        self.publisher.publish.assert_called_once_with(data)

    def test_unregister_publisher(self):
        self.metricsFactory.register_publisher(self.publisher)
        self.metricsFactory.unregister_publisher(self.publisher)
        data = {}
        self.metricsFactory.emit(data)


if __name__ == '__main__':
    unittest.main()
