import unittest
import unittest.mock

import benchmarkai.FilePublisher


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.wrap = unittest.mock.Mock()
        self.pub = benchmarkai.FilePublisher(self.wrap)

    def test_one_line_per_entry(self):
        data = {"one": "1", "two": "2"}
        self.pub.publish(data)
        self.assertEqual(2, self.wrap.write.call_count)


if __name__ == '__main__':
    unittest.main()
