import requests
from hbp_service_client.document_service.service_locator import ServiceLocator

class RequestBuilder(object):
    '''A builder to create requests'''

    def __init__(self, service_locator, method='GET', url='NO_URL'):
        '''
        Args:
           service_locator: collaborator which gets the collab services urls
           method: the http method (GET, POST...)
           url: the url to send a request to
        '''
        self._service_locator = service_locator
        self._method = method
        self._url = url

    @classmethod
    def new(cls, environment='prod'):
        '''Create new request builder

            Arguments:
                environment: The service environment to be used for the requestor

            Returns:
                A request builder instance

        '''
        return cls(ServiceLocator.new(environment))

    def _copy_and_set(self, attribute, value):
        params = {'method': self._method, 'url': self._url}
        params[attribute] = value
        return RequestBuilder(self._service_locator, **params)

    def a_get_request(self):
        return self._copy_and_set('method', 'GET')

    def to(self, url):
        return self._copy_and_set('url', url)

    def send(self):
        return requests.request(
            self._method,
            self._url
        )
