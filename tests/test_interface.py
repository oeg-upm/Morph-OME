import unittest
import os
import sys
import app as appl
from tests import prep


class InterfaceTest(unittest.TestCase):
    def test_home(self):
        app = appl.get_app(test=True)
        client = app.test_client()
        response = client.get('/')
        self.assertEquals(response.status_code, 200)

    def test_about(self):
        app = appl.get_app(test=True)
        client = app.test_client()
        response = client.get('/about')
        self.assertEquals(response.status_code, 200)

    def test_tutorial(self):
        app = appl.get_app(test=True)
        client = app.test_client()
        response = client.get('/tutorial')
        self.assertEquals(response.status_code, 200)
