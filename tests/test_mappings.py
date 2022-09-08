import unittest
import app as appl


class MappingsTest(unittest.TestCase):
    def test_rml_mappings(self):
        app = appl.get_app(test=True)
        client = app.test_client()
        response = client.post('/generate_mapping', data=dict(
            entity_class="SOMECLASS",
            entity_column='"some file"',
            file_name="FAKEFILE",
            form_val_1='http://www.w3.org/2000/01/rdf-schema#label',
            form_key_1='"Name of Water Body"',
            mapping_lang="rml"), follow_redirects=True)
        self.assertEquals(response.status_code, 200)
        self.assertNotIn('error', str(response.data).lower())
        self.assertNotIn('""', str(response.data).lower())
        self.assertNotIn('"some file"', str(response.data).lower())

