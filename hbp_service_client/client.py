'''A convenience single client that combines functionality from the different services'''

from hbp_service_client.storage_service.api import ApiClient as SAC


class Client(object):
    '''A single client that combines functionality from the different services'''

    def __init__(self, storage_client):
        super(Client, self).__init__()
        self.storage = storage_client

    @classmethod
    def new(cls, access_token, environment='prod'):
        '''create a new cross-service client'''

        return cls(
            storage_client=SAC.new(access_token, environment=environment))
