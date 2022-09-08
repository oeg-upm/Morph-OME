from __future__ import print_function
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# added this to import app.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from tests.test_upload import UploadTest
from tests.test_interface import InterfaceTest
from tests.test_util import UtilTest
from tests.test_mappings import MappingsTest

import unittest
from tests import prep


def loadTC(tc):
    return unittest.TestLoader().loadTestsFromTestCase(tc)


if __name__ == "__main__":

    prep.create_dbpedia(os.path.join(BASE_DIR, 'data', 'dbpedia'))

    cases = [
        unittest.TestLoader().loadTestsFromTestCase(UploadTest),
        loadTC(InterfaceTest),
        loadTC(UtilTest),
        loadTC(MappingsTest)
    ]

    suite = unittest.TestSuite(cases)
    result = unittest.TextTestRunner().run(suite)
    sys.exit(not result.wasSuccessful())
