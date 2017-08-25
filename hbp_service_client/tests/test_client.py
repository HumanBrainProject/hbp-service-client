import unittest
from hamcrest import (assert_that, instance_of, has_properties)

from hbp_service_client.client import Client
from hbp_service_client.storage_service.client import Client as StorageClient

class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = Client.new('access_token')

    def test_client_is_instantiable(self):
        assert_that(self.client, instance_of(Client))

    def test_client_has_storage_client(self):
        assert_that(
            self.client,
            has_properties(
                {'storage': instance_of(StorageClient)}))
