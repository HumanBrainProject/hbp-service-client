from hbp_service_client.document_service.service_locator import ServiceLocator

class RequestBuilder(object):
    '''A class to make requests'''

    def __init__(self, service_locator):
        '''
        Args:
           service_locator: collaborator which gets the collab services urls
        '''
        self._service_locator = service_locator

    @classmethod
    def new(cls, environment='prod'):
        '''Create new request builder

            Arguments:
                environment: The service environment to be used for the requestor

            Returns:
                A request builder instance

        '''
        return cls(ServiceLocator.new(environment))
