import unittest
import os
from util import get_headers_csv


class UtilTest(unittest.TestCase):
    def test_get_header_csv(self):
        headers = get_headers_csv(os.path.join("tests", "basketballplayers_mini.csv"))
        self.assertEquals(len(headers), 8)
        self.assertEquals(headers[-1], headers[-1].strip())
