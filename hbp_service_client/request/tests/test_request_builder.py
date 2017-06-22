import unittest
import httpretty
import json

from hamcrest import *

from hbp_service_client.request.request_builder import RequestBuilder as RequestBuilder

class TestRequestBuilder(unittest.TestCase):

    def setUp(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({ 'my_service': {'v3': 'https://my/service/v3'} })
        )
        self.builder = RequestBuilder.new()

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def test_should_send_a_get_request_to_the_given_url(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url',
            body='the url response'
        )

        # when
        response = self.builder.a_get_request().to('http://a.url').send()

        # then
        assert_that(response.text, equal_to('the url response'))
