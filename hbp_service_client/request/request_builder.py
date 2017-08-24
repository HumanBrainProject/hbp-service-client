import requests
from hbp_service_client.storage_service.service_locator import ServiceLocator

class RequestBuilder(object):
    '''A builder to create requests'''

    def __init__(self, service_locator=None, url=None, service_url=None, endpoint=None, headers={}, return_body=False, params={}, body=None, json_body=None, stream=False, throws=[]):
        '''
        Args:
           service_locator: collaborator which gets the collab services urls
           method: the http method (GET, POST...)
           url: the url to send a request to
           service_url: if url is not set, will be used in conjonction to `endpoint` to create the url
           endpoint: is concatenated to `service_url` to create the url
           headers: headers to add to the request as key/value pairs
           return_body: True if the body of the response should be returned, False if the response should be returned
           params: params to add to the request as key/value pairs
           body: the body of the request
           json_body: the body of the request as a json object
           stream: stream the response if True
        '''
        self._service_locator = service_locator
        self._url = url
        self._service_url = service_url
        self._endpoint = endpoint
        self._headers = headers
        self._return_body = return_body
        self._params = params
        self._body = body
        self._json_body = json_body
        self._stream = stream
        self._throws = throws

    @classmethod
    def request(cls, environment='prod'):
        '''Create new request builder

            Arguments:
                environment: The service environment to be used for the request

            Returns:
                A request builder instance

        '''
        return cls(service_locator=ServiceLocator.new(environment))

    def _copy_and_set(self, attribute, value):
        params = {
            'service_locator' : self._service_locator,
            'url'             : self._url,
            'service_url'     : self._service_url,
            'endpoint'        : self._endpoint,
            'headers'         : self._headers,
            'return_body'     : self._return_body,
            'params'          : self._params,
            'body'            : self._body,
            'json_body'       : self._json_body,
            'stream'          : self._stream,
            'throws'          : self._throws
        }
        params[attribute] = value
        return RequestBuilder(**params)

    def to(self, url):
        return self._copy_and_set('url', url)

    def to_service(self, service, version):
        service_url = self._service_locator.get_service_url(service, version)
        return self._copy_and_set('service_url', self._strip_trailing_slashes(service_url))

    def to_endpoint(self, endpoint):
        return self._copy_and_set('endpoint', self._strip_leading_slashes(endpoint))

    def _strip_leading_slashes(self, text):
        return self._strip_leading_slashes(text[1:]) if text.startswith('/') else text

    def _strip_trailing_slashes(self, text):
        return self._strip_trailing_slashes(text[:-1]) if text.endswith('/') else text

    def with_headers(self, headers):
        copy = headers.copy()
        copy.update(self._headers)
        return self._copy_and_set('headers', copy)

    def with_token(self, token):
        return self.with_headers({'Authorization': 'Bearer {}'.format(token)})

    def with_params(self, params):
        copy = params.copy()
        copy.update(self._params)
        return self._copy_and_set('params', copy)

    def return_body(self):
        return self._copy_and_set('return_body', True)

    def with_body(self, body):
        return self._copy_and_set('body', body)

    def with_json_body(self, json_body):
        return self._copy_and_set('json_body', json_body)

    def stream_response(self):
        return self._copy_and_set('stream', True)

    def throw(self, exception_class, should_throw):
        return self._copy_and_set('throws', self._throws + [(exception_class, should_throw)])

    def get(self):
        return self._send('GET')

    def post(self):
        return self._send('POST')

    def delete(self):
        return self._send('DELETE')

    def put(self):
        return self._send('PUT')

    def _send(self, method):
        url = self._url if self._url else '{}/{}'.format(self._service_url, self._endpoint)
        response = requests.request(
            method,
            url,
            headers=self._headers,
            params=self._params,
            data=self._body,
            json=self._json_body,
            stream=self._stream
        )

        self._throw_if_necessary(response, self._throws)

        if self._return_body:
             return self._extract_body(response)

        return response

    def _throw_if_necessary(self, response, throws):
        for (exception_class, should_throw) in throws:
            args = should_throw(response)
            if args != None:
                raise exception_class(args)

    def _extract_body(self, response):
        if response.headers.get('Content-Type', None) == 'application/json':
            return response.json()
        return response.text
