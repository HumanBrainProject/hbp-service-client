# pylint: disable=too-many-instance-attributes, too-many-arguments

'''A request builder to generate http requests in a fluent manner '''

import requests
from hbp_service_client.storage_service.service_locator import ServiceLocator


class RequestBuilder(object):
    '''A builder to create requests'''

    def __init__(
            self, service_locator=None, url=None, service_url=None, endpoint=None,
            headers=None, return_body=False, params=None, body=None, json_body=None,
            stream=False, throws=None):
        '''
        Args:
           service_locator: collaborator which gets the collab services urls
           method: the http method (GET, POST...)
           url: the url to send a request to
           service_url: if url is not set, will be used in conjonction to `endpoint`
                        to create the url
           endpoint: is concatenated to `service_url` to create the url
           headers: headers to add to the request as key/value pairs
           return_body: True if the body of the response should be returned,
                        False if the response should be returned
           params: params to add to the request as key/value pairs
           body: the body of the request
           json_body: the body of the request as a json object
           stream: stream the response if True
        '''
        self._service_locator = service_locator
        self._url = url
        self._service_url = service_url
        self._endpoint = endpoint
        self._headers = headers if headers is not None else {}
        self._return_body = return_body
        self._params = params if params is not None else {}
        self._body = body
        self._json_body = json_body
        self._stream = stream
        self._throws = throws if throws is not None else []

    @classmethod
    def request(cls, environment='prod'):
        '''Create new request builder

            Arguments:
                environment: The service environment to be used for the request

            Returns:
                A request builder instance

        '''
        return cls(service_locator=ServiceLocator.new(environment))

    def __copy_and_set(self, attribute, value):
        params = {
            'service_locator': self._service_locator,
            'url': self._url,
            'service_url': self._service_url,
            'endpoint': self._endpoint,
            'headers': self._headers,
            'return_body': self._return_body,
            'params': self._params,
            'body': self._body,
            'json_body': self._json_body,
            'stream': self._stream,
            'throws': self._throws
        }
        params[attribute] = value
        return RequestBuilder(**params)

    def to_url(self, url):
        '''Sets the request target url

        Args:
            url (str): The url the request should be targeted to

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('url', url)

    def to_service(self, service, version):
        '''Sets the service name and version the request should target

        Args:
            service (str): The name of the service as displayed in the services.json file
            version (str): The version of the service as displayed in the services.json file

        Returns:
            The request builder instance in order to chain calls
        '''
        service_url = self._service_locator.get_service_url(service, version)
        return self.__copy_and_set('service_url', self.__strip_trailing_slashes(service_url))

    def to_endpoint(self, endpoint):
        '''Sets the endpoint of the service the request should target

        Args:
            endpoint (str): The endpoint that will be concatenated to the service url

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('endpoint', self.__strip_leading_slashes(endpoint))

    def __strip_leading_slashes(self, text):
        return self.__strip_leading_slashes(text[1:]) if text.startswith('/') else text

    def __strip_trailing_slashes(self, text):
        return self.__strip_trailing_slashes(text[:-1]) if text.endswith('/') else text

    def with_headers(self, headers):
        '''Adds headers to the request

        Args:
            headers (dict): The headers to add the request headers

        Returns:
            The request builder instance in order to chain calls
        '''
        copy = headers.copy()
        copy.update(self._headers)
        return self.__copy_and_set('headers', copy)

    def with_token(self, token):
        '''Sets the token in the request `Authorization` header

        Args:
            token (str): The token to add the `Authorization` header

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.with_headers({'Authorization': 'Bearer {}'.format(token)})

    def with_params(self, params):
        '''Adds parameters to the request params

        Args:
            params (dict): The parameters to add to the request params

        Returns:
            The request builder instance in order to chain calls
        '''
        copy = params.copy()
        copy.update(self._params)
        return self.__copy_and_set('params', copy)

    def return_body(self):
        '''Indicates that the body of the response should be returned after the request is sent
           By default the response object is returned

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('return_body', True)

    def with_body(self, body):
        '''Sets the body of the request

        Args:
            body: The body of the request

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('body', body)

    def with_json_body(self, json_body):
        '''Sets the body of the request with a json object

        Args:
            json_body (dict): The json object to send with the request

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('json_body', json_body)

    def stream_response(self):
        '''Indicates that the reponse should be streamed

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('stream', True)

    def throw(self, exception_class, should_throw):
        '''Defines if the an exception should be thrown after the request is sent

        Args:
            exception_class (class): The class of the exception to instantiate
            should_throw (function): The predicate that should indicate if the exception
                should be thrown. This function will be called with the response as a parameter

        Returns:
            The request builder instance in order to chain calls
        '''
        return self.__copy_and_set('throws', self._throws + [(exception_class, should_throw)])

    def get(self):
        '''Sends the request as parametrized with the GET verb

        Returns:
            The response object or body depending of the parametrization

        Raises:
            Any exception parametrized with the `throw` method
        '''
        return self.__send('GET')

    def post(self):
        '''Sends the request as parametrized with the POST verb

        Returns:
            The response object or body depending of the parametrization

        Raises:
            Any exception parametrized with the `throw` method
        '''
        return self.__send('POST')

    def delete(self):
        '''Sends the request as parametrized with the DELETE verb

        Returns:
            The response object or body depending of the parametrization

        Raises:
            Any exception parametrized with the `throw` method
        '''
        return self.__send('DELETE')

    def put(self):
        '''Sends the request as parametrized with the PUT verb

        Returns:
            The response object or body depending of the parametrization

        Raises:
            Any exception parametrized with the `throw` method
        '''
        return self.__send('PUT')

    def __send(self, method):
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

        self.__throw_if_necessary(response, self._throws)

        if self._return_body:
            return self.__extract_body(response)

        return response

    @staticmethod
    def __throw_if_necessary(response, throws):
        for (exception_class, should_throw) in throws:
            args = should_throw(response)
            if args is not None:
                raise exception_class(args)

    @staticmethod
    def __extract_body(response):
        if response.headers.get('Content-Type', None) == 'application/json':
            return response.json()
        return response.text
