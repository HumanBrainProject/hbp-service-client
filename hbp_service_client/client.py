# pylint: disable=too-few-public-methods

'''A convenience single client that combines functionality from the different services'''

from hbp_service_client.storage_service.client import Client as StorageClient


class Client(object):
    '''A single client that combines functionalities from the different services'''

    def __init__(self, storage_client):
        super(Client, self).__init__()
        self.storage = storage_client

    @classmethod
    def new(cls, access_token, environment='prod'):
        '''Creates a new cross-service client.'''

        return cls(
            storage_client=StorageClient.new(access_token, environment=environment))
