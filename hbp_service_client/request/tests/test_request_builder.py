import unittest

from hbp_service_client.request.request_builder import RequestBuilder

class TestRequestBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = RequestBuilder.new()

    def test_ready(self):
        print 'ready!'
