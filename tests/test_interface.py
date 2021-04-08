import unittest
import app as appl


class InterfaceTest(unittest.TestCase):
    def test_home(self):
        app = appl.get_app(test=True)
        client = app.test_client()
        response = client.get('/')
        self.assertEquals(response.status_code, 200)
