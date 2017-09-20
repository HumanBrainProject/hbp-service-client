import json
import unittest
import httpretty
from hamcrest import (
    assert_that, equal_to, has_entries)

from hbp_service_client.request.request_builder import RequestBuilder as RequestBuilder

class TestRequestBuilder(unittest.TestCase):

    def setUp(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({'my_service': {
                'v3': 'https://my/service/v3',
                'with_trailing_slash': 'https://my/service/v3/'}}))
        self.request = RequestBuilder.request()

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
        response = self.request.to_url('http://a.url').get()

        # then
        assert_that(response.text, equal_to('the url response'))

    def test_should_send_a_get_request_to_the_given_service_endpoint(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'https://my/service/v3/to/endpoint/',
            body='the endpoint response'
        )

        # when
        response = self.request \
            .to_service('my_service', 'v3') \
            .to_endpoint('to/endpoint/') \
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
        response = self.request.to_url('http://a.url').post()

        # then
        assert_that(response.text, equal_to('the post response'))

    def test_should_send_a_delete_request_to_the_given_url(self):
        # given
        httpretty.register_uri(
            httpretty.DELETE, 'http://a.url',
            body='the delete response'
        )

        # when
        response = self.request.to_url('http://a.url').delete()

        # then
        assert_that(response.text, equal_to('the delete response'))

    def test_should_send_a_put_request_to_the_given_url(self):
        # given
        httpretty.register_uri(
            httpretty.PUT, 'http://a.url',
            body='the put response'
        )

        # when
        response = self.request.to_url('http://a.url').put()

        # then
        assert_that(response.text, equal_to('the put response'))


    def test_should_send_a_request_with_the_given_headers(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_headers({'my_header': 'its value'}) \
            .get()

        # then
        assert_that(
            httpretty.last_request().headers,
            has_entries(my_header='its value')
        )

    def test_should_accumulate_headers(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_headers({'first_header': 'its value'}) \
            .with_headers({'second_header': 'its value'}) \
            .get()

        # then
        assert_that(
            httpretty.last_request().headers,
            has_entries(first_header='its value')
        )
        assert_that(
            httpretty.last_request().headers,
            has_entries(second_header='its value')
        )

    def test_should_add_the_access_token_header(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_token('my-token') \
            .get()

        # then
        assert_that(
            httpretty.last_request().headers,
            has_entries(Authorization='Bearer my-token')
        )

    def test_should_return_the_body_of_the_response(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url',
            body='some content'
        )

        # when
        response = self.request \
            .to_url('http://a.url') \
            .return_body() \
            .get()

        # then
        assert_that(response, equal_to('some content'))

    def test_should_return_the_body_of_the_response_as_json(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url',
            body=json.dumps({'some_key': {'another_one': 'some value'}}),
            content_type="application/json"
        )

        # when
        response = self.request \
            .to_url('http://a.url') \
            .return_body() \
            .get()

        # then
        assert_that(response, equal_to({'some_key': {'another_one': 'some value'}}))

    def test_should_add_the_given_params_to_the_query_string(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_params({'a_param': 'its value', 'another_one': 'another value'}) \
            .get()

        # then
        assert_that(
            httpretty.last_request().querystring,
            has_entries(a_param=['its value'])
        )
        assert_that(
            httpretty.last_request().querystring,
            has_entries(another_one=['another value'])
        )

    def test_should_accumulate_params(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_params({'a_param': 'its value'}) \
            .with_params({'another_one': 'another value'}) \
            .get()

        # then
        assert_that(
            httpretty.last_request().querystring,
            has_entries(a_param=['its value'])
        )
        assert_that(
            httpretty.last_request().querystring,
            has_entries(another_one=['another value'])
        )

    def test_should_set_the_body_of_the_request(self):
        # given
        httpretty.register_uri(
            httpretty.POST, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_body('some content') \
            .post()

        # then
        assert_that(
            httpretty.last_request().body,
            equal_to(b'some content')
        )

    def test_should_set_the_body_of_the_request_with_provided_json(self):
        # given
        httpretty.register_uri(
            httpretty.POST, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_json_body({'a-key': 'its value', 'another-key': {'some-key': 'some value'}}) \
            .post()

        # then
        assert_that(
            json.loads(httpretty.last_request().body.decode()),
            equal_to({'a-key': 'its value', 'another-key': {'some-key': 'some value'}})
        )

    def test_should_set_the_content_type_when_sending_json(self):
        # given
        httpretty.register_uri(
            httpretty.POST, 'http://a.url'
        )

        # when
        self.request \
            .to_url('http://a.url') \
            .with_json_body({'a-key': 'its value'}) \
            .post()

        # then
        assert_that(
            httpretty.last_request().headers,
            has_entries({'Content-Type': 'application/json'})
        )

    def test_should_stream_the_response(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'http://a.url',
            body='#'*30
        )

        # when
        with self.request.to_url('http://a.url').stream_response().get() as response:

            # then
            content = b''
            for chunk in response.iter_content(chunk_size=10):
                assert_that(chunk, equal_to(b'#'*10))
                content += chunk

            assert_that(content, equal_to(b'#'*30))

    def test_should_handle_joining_slash_between_service_and_endpoint(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'https://my/service/v3/to/endpoint/',
            body='the endpoint response'
        )

        # when
        # service with NO trailing slash, endpoint with leading slash
        response = self.request \
            .to_service('my_service', 'v3') \
            .to_endpoint('/to/endpoint/') \
            .get()

        # then
        assert_that(response.text, equal_to('the endpoint response'))

        # when
        # service with trailing slash, endpoint with NO leading slash
        response = self.request \
            .to_service('my_service', 'with_trailing_slash') \
            .to_endpoint('to/endpoint/') \
            .get()

        # then
        assert_that(response.text, equal_to('the endpoint response'))

        # when
        # service with trailing slash, endpoint with leading slash
        response = self.request \
            .to_service('my_service', 'with_trailing_slash') \
            .to_endpoint('/to/endpoint/') \
            .get()

        # then
        assert_that(response.text, equal_to('the endpoint response'))

    def test_should_throw_exception_if_test_returns_a_message(self):
        # given
        class NotFoundException(Exception):
            pass

        httpretty.register_uri(
            httpretty.GET, 'http://some.url',
            status=404
        )

        # when
        try:
            self.request \
                .to_url('http://some.url') \
                .throw(NotFoundException, lambda resp: 'Not found' if resp.status_code == 404 else None) \
                .get()
            self.fail('Exception has not been thrown')

        # then
        except NotFoundException as ex:
            assert_that(ex.args[0], equal_to('Not found'))

    def test_should_not_throw_exception_if_test_returns_none(self):
        # given
        class NotFoundException(Exception):
            pass

        httpretty.register_uri(
            httpretty.GET, 'http://some.url',
            status=200
        )

        # when
        self.request \
            .to_url('http://some.url') \
            .throw(NotFoundException, lambda resp: 'Not found' if resp.status_code == 404 else None) \
            .get()

        # then
        # no exception
