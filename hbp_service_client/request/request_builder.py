import requests
from hbp_service_client.document_service.service_locator import ServiceLocator

class RequestBuilder(object):
    '''A builder to create requests'''

    def __init__(self, service_locator=None, url=None, service_url=None, endpoint=None):
        '''
        Args:
           service_locator: collaborator which gets the collab services urls
           method: the http method (GET, POST...)
           url: the url to send a request to
           service_url: if url is not set, will be used in conjonction to `endpoint` to create the url
           endpoint: is concatenated to `service_url` to create the url
        '''
        self._service_locator = service_locator
        self._url = url
        self._service_url = service_url
        self._endpoint = endpoint

    @classmethod
    def request(cls, environment='prod'):
        '''Create new request builder

            Arguments:
                environment: The service environment to be used for the requestor

            Returns:
                A request builder instance

        '''
        return cls(service_locator=ServiceLocator.new(environment))

    def _copy_and_set(self, attribute, value):
        params = {
            'service_locator':  self._service_locator,
            'url':              self._url,
            'service_url':      self._service_url,
            'endpoint':         self._endpoint
        }
        params[attribute] = value
        return RequestBuilder(**params)

    def to(self, url):
        return self._copy_and_set('url', url)

    def to_service(self, service, version):
        return self._copy_and_set('service_url', self._service_locator.get_service_url(service, version))

    def to_endpoint(self, endpoint):
        return self._copy_and_set('endpoint', endpoint)

    def get(self):
        return self._send('GET')

    def post(self):
        return self._send('POST')

    def delete(self):
        return self._send('DELETE')

    def put(self):
        return self._send('PUT')

    def _send(self, method):
        url = self._url if self._url else '{}/{}/'.format(self._service_url, self._endpoint)
        return requests.request(
            method,
            url
        )
