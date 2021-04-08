from __future__ import print_function
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# added this to import app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_upload import UploadTest
from tests.test_interface import InterfaceTest

import unittest


def loadTC(tc):
    return unittest.TestLoader().loadTestsFromTestCase(tc)


if __name__ == "__main__":

    cases = [
        unittest.TestLoader().loadTestsFromTestCase(UploadTest),
        loadTC(InterfaceTest),
    ]

    suite = unittest.TestSuite(cases)
    result = unittest.TextTestRunner().run(suite)
    sys.exit(not result.wasSuccessful())
