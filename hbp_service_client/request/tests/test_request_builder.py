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
        response = self.builder.to('http://a.url').get()

        # then
        assert_that(response.text, equal_to('the url response'))

    def test_should_send_a_get_request_to_the_given_service_endpoint(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'https://my/service/v3/to/endpoint/',
            body='the endpoint response'
        )

        # when
        response = self.builder \
            .to_service('my_service', 'v3') \
            .to_endpoint('to/endpoint') \
            .get()

        # then
        assert_that(response.text, equal_to('the endpoint response'))

    def test_should_send_a_post_request_to_the_given_url(self):
        # given
        httpretty.register_uri(
            httpretty.POST, 'http://a.url',
            body='the post response'
        )

        # when
        response = self.builder.to('http://a.url').post()

        # then
        assert_that(response.text, equal_to('the post response'))

    def test_should_send_a_delete_request_to_the_given_url(self):
        # given
        httpretty.register_uri(
            httpretty.DELETE, 'http://a.url',
            body='the delete response'
        )

        # when
        response = self.builder.to('http://a.url').delete()

        # then
        assert_that(response.text, equal_to('the delete response'))

    def test_should_send_a_put_request_to_the_given_url(self):
        # given
        httpretty.register_uri(
            httpretty.PUT, 'http://a.url',
            body='the put response'
        )

        # when
        response = self.builder.to('http://a.url').put()

        # then
        assert_that(response.text, equal_to('the put response'))
