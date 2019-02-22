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

        args = self.wrap.write.call_args_list

        arg0 = str(args[0][0])
        self.assertIn("one", arg0)
        self.assertIn("1", arg0)

        arg1 = str(args[1][0])
        self.assertIn("two", arg1)
        self.assertIn("2", arg1)

        self.assertEqual(2, self.wrap.write.call_count)


if __name__ == '__main__':
    unittest.main()
