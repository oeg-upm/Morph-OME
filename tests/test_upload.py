import unittest
import app as appl


class UploadTest(unittest.TestCase):
    def test_csv(self):
        app = appl.get_app(test=True)
        client = app.test_client()
        response = client.post('/editor', data=dict(
            source="https://raw.githubusercontent.com/oeg-upm/morph-rdb/master/morph-examples/examples-csv/SPORT.csv",
            ontologies=['dbpedia'],
            kg="",
    ), follow_redirects=True)
        self.assertEquals(response.status_code, 200)
        self.assertNotIn('error', str(response.data).lower())
