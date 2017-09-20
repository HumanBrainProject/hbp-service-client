import json
import unittest
import httpretty
from hamcrest import (assert_that, has_properties, not_none)

from hbp_service_client.client import Client

class TestClient(unittest.TestCase):

    def setUp(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET,
            'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({'document': {'v1': 'https://document/service'}})
        )
        self.client = Client.new('access_token')

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def test_client_is_instantiable(self):
        assert_that(self.client, not_none())

    def test_client_has_storage_client(self):
        assert_that(
            self.client,
            has_properties({'storage': not_none()}))
