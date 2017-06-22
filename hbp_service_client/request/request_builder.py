import requests
from hbp_service_client.document_service.service_locator import ServiceLocator

class RequestBuilder(object):
    '''A builder to create requests'''

    def __init__(self, service_locator, method='GET', url=None, service_url=None, endpoint=None):
        '''
        Args:
           service_locator: collaborator which gets the collab services urls
           method: the http method (GET, POST...)
           url: the url to send a request to
        '''
        self._service_locator = service_locator
        self._method = method
        self._url = url
        self._service_url = service_url
        self._endpoint = endpoint

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
        params = {'method': self._method, 'url': self._url, 'service_url': self._service_url, 'endpoint': self._endpoint}
        params[attribute] = value
        return RequestBuilder(self._service_locator, **params)

    def a_get_request(self):
        return self._copy_and_set('method', 'GET')

    def to(self, url):
        return self._copy_and_set('url', url)

    def to_service(self, service, version):
        return self._copy_and_set('service_url', self._service_locator.get_service_url(service, version))

    def to_endpoint(self, endpoint):
        return self._copy_and_set('endpoint', endpoint)

    def send(self):
        url = self._url if self._url else '{service_url}/{endpoint}/'.format(service_url=self._service_url, endpoint=self._endpoint)
        return requests.request(
            self._method,
            url
        )
