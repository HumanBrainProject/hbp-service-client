import unittest
from mock import Mock
import httpretty
import json
import re
import mock

from hamcrest import *

from hbp_service_client.document_service.highlevel import StorageClient

class TestStorageClient(unittest.TestCase):
    def setUp(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({ 'document': {'v1': 'https://document/service'} })
        )
        self.client = StorageClient.new('access_token')

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def register_uri(self, uri, returns):
        httpretty.register_uri(
            httpretty.GET, re.compile(re.escape(uri)),
            match_querystring=True,
            body=json.dumps(returns),
            content_type="application/json"
        )

    #
    # ls
    #

    def test_ls_should_return_an_empty_list_for_an_empty_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=my_empty_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1',
            returns={'next': None, 'results': []}
        )

        # when
        file_names = self.client.ls('my_empty_project')

        # then
        assert_that(file_names, equal_to([]))


    def test_ls_should_return_the_files_of_the_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=my_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1',
            returns={'next': None, 'results': [{'name': 'file1', 'entity_type': 'file'}, {'name': 'file2', 'entity_type': 'file'}]}
        )

        # when
        file_names = self.client.ls('my_project')

        # then
        assert_that(file_names, equal_to(['file1', 'file2']))


    def test_ls_should_return_the_folders_of_the_project_with_a_leading_slash(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=my_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1',
            returns={'next': None, 'results': [{'name': 'folder1', 'entity_type': 'folder'}, {'name': 'folder2', 'entity_type': 'folder'}]}
        )

        # when
        file_names = self.client.ls('my_project')

        # then
        assert_that(file_names, equal_to(['/folder1', '/folder2']))


    def test_ls_should_load_all_the_paginated_files_of_the_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=my_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1',
            returns={'next': 'link.to.next.page', 'results': [{'name': 'file1', 'entity_type': 'file'}, {'name': 'folder1', 'entity_type': 'folder'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=2',
            returns={'next': 'link.to.next.page', 'results': [{'name': 'file2', 'entity_type': 'file'}, {'name': 'folder2', 'entity_type': 'folder'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=3',
            returns={'next': None, 'results': [{'name': 'file3', 'entity_type': 'file'}, {'name': 'folder3', 'entity_type': 'folder'}]}
        )

        # when
        file_names = self.client.ls('my_project')

        # then
        assert_that(file_names, equal_to(['file1', '/folder1', 'file2', '/folder2', 'file3', '/folder3']))


    #
    # download_file
    #

    def test_download_file_checks_entity_is_a_file(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=path-to-something',
            returns={'entity_type': 'not a file'}
        )

        # then
        assert_that(
            calling(self.client.download_file).with_args('path-to-something', 'path/to/target'),
            raises(AssertionError)
        )


    @mock.patch('hbp_service_client.document_service.highlevel.open', create=True)
    def test_download_file_should_download_file_content_into_a_local_file(self, mock_open):
        # given
        self.register_uri(
            'https://document/service/entity/?path=path-to-file',
            returns={'entity_type': 'file', 'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/file/e2c25c1b-1234-4cf6-b8d2-271e628a9a56/content/secure_link/',
            returns={'signed_url':'/signed/url/to/the/file'}
        )
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/signed/url/to/the/file',
            body='some content'
        )

        # when
        self.client.download_file('path-to-file', 'target.file')

        # then
        mock_open.assert_called_once_with('target.file', 'wb')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_once_with('some content')


    @mock.patch('hbp_service_client.document_service.highlevel.open', create=True)
    def test_download_file_should_download_file_content_in_1024_chunks(self, mock_open):
        # given
        self.register_uri(
            'https://document/service/entity/?path=path-to-file',
            returns={'entity_type': 'file', 'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/file/e2c25c1b-1234-4cf6-b8d2-271e628a9a56/content/secure_link/',
            returns={'signed_url':'/signed/url/to/the/file'}
        )
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/signed/url/to/the/file',
            body='#'*2048
        )

        # when
        self.client.download_file('path-to-file', 'target.file')

        # then
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_twice_with('#'*1024)
