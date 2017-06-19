import unittest
from mock import Mock
import httpretty
import json

from hbp_service_client.document_service.highlevel import StorageClient

class TestStorageClient(unittest.TestCase):
    def setUp(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({ 'document': {'v1': 'https://dummy.host/fake/document/service'} })
        )
        self.client = StorageClient.new('access_token')

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    #
    # ls
    #

    def test_ls(self):
        return 0
