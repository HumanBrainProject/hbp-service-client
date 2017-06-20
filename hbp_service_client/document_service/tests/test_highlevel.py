import unittest
from mock import Mock
import httpretty
import json
import re

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
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=file',
            returns={'next': None, 'results': []}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=folder',
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
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=file',
            returns={'next': None, 'results': [{'name': 'file1'}, {'name': 'file2'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=folder',
            returns={'next': None, 'results': []}
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
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=file',
            returns={'next': None, 'results': []}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=folder',
            returns={'next': None, 'results': [{'name': 'folder1'}, {'name': 'folder2'}]}
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
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=file',
            returns={'next': 'link.to.next.page', 'results': [{'name': 'file1'}, {'name': 'file2'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=2&page_size=100&entity_type=file',
            returns={'next': 'link.to.next.page', 'results': [{'name': 'file3'}, {'name': 'file4'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=3&page_size=100&entity_type=file',
            returns={'next': None, 'results': [{'name': 'file5'}, {'name': 'file6'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=folder',
            returns={'next': None, 'results': []}
        )

        # when
        file_names = self.client.ls('my_project')

        # then
        assert_that(file_names, equal_to(['file1', 'file2', 'file3', 'file4', 'file5', 'file6']))


    def test_ls_should_load_all_the_paginated_folders_of_the_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=my_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=file',
            returns={'next': None, 'results': []}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=1&page_size=100&entity_type=folder',
            returns={'next': 'link.to.next.page', 'results': [{'name': 'folder1'}, {'name': 'folder2'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=2&page_size=100&entity_type=folder',
            returns={'next': 'link.to.next.page', 'results': [{'name': 'folder3'}, {'name': 'folder4'}]}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/?page=3&page_size=100&entity_type=folder',
            returns={'next': None, 'results': [{'name': 'folder5'}, {'name': 'folder6'}]}
        )

        # when
        file_names = self.client.ls('my_project')

        # then
        assert_that(file_names, equal_to(['/folder1', '/folder2', '/folder3', '/folder4', '/folder5', '/folder6']))
