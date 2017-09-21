'''Unit tests for hbp_service_client.storage_service.client'''

import json
import re
import pytest
import mock
import httpretty
from hamcrest import (assert_that, calling, raises, equal_to, has_properties)


from hbp_service_client.storage_service.client import Client
from hbp_service_client.storage_service.exceptions import (
    StorageNotFoundException, StorageArgumentException)

class TestClient(object):
    __BAD_PATHS = [123, 'foo', '', '/']

    def setup_method(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({'document': {'v1': 'https://document/service'}})
        )
        self.client = Client.new('access_token')

    @staticmethod
    def teardown_method():
        httpretty.disable()
        httpretty.reset()

    @staticmethod
    def register_uri(uri, returns):
        httpretty.register_uri(
            httpretty.GET, re.compile(re.escape(uri)),
            match_querystring=True,
            body=json.dumps(returns),
            content_type="application/json"
        )

    #
    # ls
    #
    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_list_verifies_input_path(self, path):
        assert_that(
            calling(self.client.list).with_args(path),
            raises(StorageArgumentException))

    def test_list_should_not_accept_files(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fmyproject%2Fmyfile',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56', 'entity_type': 'file'}
        )

        # then
        assert_that(
            calling(self.client.list).with_args('/myproject/myfile'),
            raises(StorageArgumentException)
        )

    def test_list_should_return_an_empty_list_for_an_empty_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fmy_empty_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56', 'entity_type': 'project'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/',
            returns={'next': None, 'results': []}
        )

        # when
        file_names = self.client.list('/my_empty_project')

        # then
        assert_that(file_names, equal_to([]))


    def test_list_should_return_the_files_of_the_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fmy_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56', 'entity_type': 'project'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/',
            returns={
                'next': None,
                'results': [{'name': 'file1', 'entity_type': 'file'},
                            {'name': 'file2', 'entity_type': 'file'}]}
        )

        # when
        file_names = self.client.list('/my_project')

        # then
        assert_that(file_names, equal_to(['file1', 'file2']))


    def test_list_should_return_the_folders_of_the_project_with_a_leading_slash(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fmy_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56', 'entity_type': 'project'}
        )
        self.register_uri(
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/',
            returns={
                'next': None,
                'results': [{'name': 'folder1', 'entity_type': 'folder'},
                            {'name': 'folder2', 'entity_type': 'folder'}]}
        )

        # when
        file_names = self.client.list('/my_project')

        # then
        assert_that(file_names, equal_to(['/folder1', '/folder2']))


    def test_list_should_load_all_the_paginated_files_of_the_project(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fmy_project',
            returns={'uuid': 'e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56', 'entity_type': 'project'}
        )
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/folder/e2c25c1b-f6a9-4cf6-b8d2-271e628a9a56/children/',
            responses=[
                httpretty.Response(
                    body=json.dumps({
                        'next': 'link.to.next.page',
                        'results': [{'name': 'file1', 'entity_type': 'file'},
                                    {'name': 'folder1', 'entity_type': 'folder'}]}),
                    content_type='application/json'),
                httpretty.Response(
                    body=json.dumps({
                        'next': 'link.to.next.page',
                        'results': [{'name': 'file2', 'entity_type': 'file'},
                                    {'name': 'folder2', 'entity_type': 'folder'}]}),
                    content_type='application/json'),
                httpretty.Response(
                    body=json.dumps({
                        'next': None,
                        'results': [{'name': 'file3', 'entity_type': 'file'},
                                    {'name': 'folder3', 'entity_type': 'folder'}]}),
                    content_type='application/json')
            ]
        )

        # when
        file_names = self.client.list('/my_project')

        # then
        assert_that(
            file_names,
            equal_to(['file1', '/folder1', 'file2', '/folder2', 'file3', '/folder3']))


    #
    # download_file
    #

    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_dowload_file_validates_path(self, path):
        assert_that(
            calling(self.client.download_file).with_args(path, 'valid_target_path'),
            raises(StorageArgumentException))

    def test_download_file_checks_entity_is_a_file(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Fsomething',
            returns={'entity_type': 'not a file'}
        )

        # then
        assert_that(
            calling(self.client.download_file).with_args('/path/to/something', 'path/to/target'),
            raises(StorageArgumentException)
        )


    @mock.patch('hbp_service_client.storage_service.client.open', create=True)
    def test_download_file_should_download_file_content_into_a_local_file(self, mock_open):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Ffile',
            returns={
                'entity_type': 'file',
                'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
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
        self.client.download_file('/path/to/file', 'target.file')

        # then
        mock_open.assert_called_once_with('target.file', 'wb')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_once_with(b'some content')


    @mock.patch('hbp_service_client.storage_service.client.open', create=True)
    def test_download_file_should_download_file_content_in_1024_chunks(self, mock_open):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Ffile',
            returns={
                'entity_type': 'file',
                'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
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
        self.client.download_file('/path/to/file', 'target.file')

        # then
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_has_calls(
            [mock.call(b'#'*1024), mock.call(b'#'*1024)])


    #
    # exists
    #

    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_exists_validates_path(self, path):
        assert_that(
            calling(self.client.exists).with_args(path),
            raises(StorageArgumentException))

    def test_exists_should_return_false_if_entity_does_not_exist(self):
        # given
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/entity/?path=%2Fpath%2Fto%2Fnothing',
            status=404
        )

        # when
        exists = self.client.exists('/path/to/nothing')

        # then
        assert_that(exists, equal_to(False))


    def test_exists_should_return_false_if_entity_has_no_uuid(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Fno%2Fuuid',
            returns={'entity_type': 'file'}
        )

        # when
        exists = self.client.exists('/path/to/no/uuid')

        # then
        assert_that(exists, equal_to(False))


    def test_exists_should_return_true_if_entity_exists(self):
        # given
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Fentity',
            returns={'entity_type': 'file', 'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
        )

        # when
        exists = self.client.exists('/path/to/entity')

        # then
        assert_that(exists, equal_to(True))


    #
    # get_parents
    #

    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_get_parent_validates_path(self, path):
        assert_that(
            calling(self.client.get_parent).with_args(path),
            raises(StorageArgumentException))

    def test_get_parent_doesnt_accept_projects(self):
        assert_that(
            calling(self.client.get_parent).with_args('/project'),
            raises(StorageArgumentException))

    def test_get_parent_should_throw_exception_if_parent_does_not_exist(self):
        # given the parent does not exist
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/entity/?path=%2Fpath%2Fto%2Fparent',
            status=404
        )

        # then
        assert_that(
            calling(self.client.get_parent).with_args('/path/to/parent/entity'),
            raises(StorageNotFoundException)
        )


    def test_get_parent_should_return_the_parent(self):
        # given the parent exists
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Fparent',
            returns='parent entity'
        )

        # when
        parent = self.client.get_parent('/path/to/parent/entity')

        # then
        assert_that(parent, equal_to('parent entity'))


    #
    # mkdir
    #

    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_mkdir_validates_path(self, path):
        assert_that(
            calling(self.client.mkdir).with_args(path),
            raises(StorageArgumentException))

    def test_mkdir_doesnt_accept_projects(self):
        assert_that(
            calling(self.client.mkdir).with_args('/project'),
            raises(StorageArgumentException))

    def test_mkdir_should_throw_an_exception_if_parent_folder_does_not_exist(self):
        # given the parent folder does not exist
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/entity/?path=%2Fpath%2Fto%2Fparent',
            status=404
        )

        # then
        assert_that(
            calling(self.client.mkdir).with_args('/path/to/parent/folder_to_create'),
            raises(StorageNotFoundException)
        )


    def test_mkdir_should_create_the_given_folder_under_its_parent(self):
        # given the parent folder is found
        parent_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Fparent',
            returns={'uuid': parent_uuid}
        )

        # and the creation of the folder works
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/folder/',
            status=201
        )

        # when
        self.client.mkdir('/path/to/parent/folder_to_create')

        # then
        request_body = json.loads(httpretty.last_request().body.decode())
        assert_that(
            request_body['parent'],
            equal_to(parent_uuid)
        )


    def test_mkdir_should_create_the_given_folder_with_its_name(self):
        # given the parent folder is found
        self.register_uri(
            'https://document/service/entity/?path=%2Fpath%2Fto%2Fparent',
            returns={'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
        )

        # and the creation of the folder works
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/folder/',
            status=201
        )

        # when
        self.client.mkdir('/path/to/parent/folder_to_create')

        # then
        request_body = json.loads(httpretty.last_request().body.decode())
        assert_that(
            request_body['name'],
            equal_to('folder_to_create')
        )


    #
    # upload_file
    #

    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_upload_file_validates_path(self, path):
        assert_that(
            calling(self.client.upload_file).with_args(dest_path=path, local_file=None, mimetype=None),
            raises(StorageArgumentException))

    def test_upload_file_should_check_if_destination_file_contains_name(self):
        assert_that(
            calling(self.client.upload_file).with_args(dest_path='path/to/a/folder/', local_file=None, mimetype=None),
            raises(StorageArgumentException)
        )


    def test_upload_file_should_check_if_local_file_is_not_a_folder(self):
        assert_that(
            calling(self.client.upload_file).with_args(local_file='path/to/a/folder/', dest_path='', mimetype=None),
            raises(StorageArgumentException)
        )


    def test_test_upload_should_throw_an_exception_if_destination_folder_does_not_exist(self):
        # given the parent folder does not exist
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/entity/?path=%2Fdest%2Fparent',
            status=404
        )

        # then
        assert_that(
            calling(self.client.upload_file).with_args(
                dest_path='/dest/parent/file_to_create',
                local_file='local/file_to_upload',
                mimetype=None),
            raises(StorageNotFoundException)
        )


    @mock.patch('hbp_service_client.storage_service.api.open', create=True)
    def test_upload_should_create_the_destination_file_under_its_destination_folder(self, mock_open):
        # given  the parent folder is found
        parent_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'
        self.register_uri(
            'https://document/service/entity/?path=%2Fdest%2Fparent',
            returns={'uuid': parent_uuid}
        )

        # and the creation of the file works
        file_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a1256'
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/',
            status=201,
            body=json.dumps({'uuid': file_uuid}),
            content_type="application/json"
        )

        # and the upload works
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(file_uuid),
            adding_headers={'ETag':'some_etag'}
        )

        # and the content of the local file is
        mock_open.return_value = ''

        # when
        self.client.upload_file(
            dest_path='/dest/parent/file_to_create',
            local_file='local/file_to_upload',
            mimetype=None
        )

        # then
        create_file_request = find_sent_request(lambda req: req.path == '/service/file/')
        request_body = json.loads(create_file_request.body.decode())
        assert_that(
            request_body['parent'],
            equal_to(parent_uuid)
        )


    @mock.patch('hbp_service_client.storage_service.api.open', create=True)
    def test_upload_should_create_the_destination_file_with_its_name(self, mock_open):
        # given  the parent folder is found
        self.register_uri(
            'https://document/service/entity/?path=%2Fdest%2Fparent',
            returns={'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
        )

        # and the creation of the file works
        file_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a1256'
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/',
            status=201,
            body=json.dumps({'uuid': file_uuid}),
            content_type="application/json"
        )

        # and the upload works
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(file_uuid),
            adding_headers={'ETag':'some_etag'}
        )

        # and the content of the local file is
        mock_open.return_value = ''

        # when
        self.client.upload_file(
            dest_path='/dest/parent/file_to_create',
            local_file='local/file_to_upload',
            mimetype=None
        )

        # then
        create_file_request = find_sent_request(lambda req: req.path == '/service/file/')
        request_body = json.loads(create_file_request.body.decode())
        assert_that(
            request_body['name'],
            equal_to('file_to_create')
        )


    @mock.patch('hbp_service_client.storage_service.api.open', create=True)
    def test_upload_should_create_the_destination_file_with_the_content_of_the_local_file(self, mock_open):
        # given  the parent folder is found
        self.register_uri(
            'https://document/service/entity/?path=%2Fdest%2Fparent',
            returns={'uuid': 'e2c25c1b-1234-4cf6-b8d2-271e628a9a56'}
        )

        # and the creation of the file works
        file_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a1256'
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/',
            status=201,
            body=json.dumps({'uuid': file_uuid}),
            content_type="application/json"
        )

        # and the upload works
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(file_uuid),
            adding_headers={'ETag':'some_etag'}
        )

        # and the content of the local file is
        mock_open.return_value = 'content of the local file'

        # when
        self.client.upload_file(
            dest_path='/dest/parent/file_to_create',
            local_file='local/file_to_upload',
            mimetype=None
        )

        # then
        assert_that(
            httpretty.last_request().body.decode(),
            equal_to('content of the local file')
        )

    #
    # delete
    #

    @pytest.mark.parametrize('path', __BAD_PATHS)
    def test_delete_should_validate_the_path(self, path):
        assert_that(
            calling(self.client.delete).with_args(path),
            raises(StorageArgumentException))

    def test_delete_should_not_accept_projects(self):
        assert_that(
            calling(self.client.delete).with_args('/foo'),
            raises(StorageArgumentException))

    def test_delete_should_reject_non_empty_folders(self):
        # given
        folder_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a1256'
        # the folder exists
        self.register_uri(
            'https://document/service/entity/?path=%2Ffoo%2Fbar',
            returns={'uuid': folder_uuid, 'entity_type': 'folder'}
        )
        # and it has children
        self.register_uri(
            'https://document/service/folder/{}/children/'.format(folder_uuid),
            returns={'count': 1}
        )

        # then
        assert_that(
            calling(self.client.delete).with_args('/foo/bar'),
            raises(StorageArgumentException))

    def test_delete_should_delete_empty_folder_from_storage(self):
        # given
        folder_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a1256'
        endpoint = '/folder/{}/'.format(folder_uuid)
        # the folder exists
        self.register_uri(
            'https://document/service/entity/?path=%2Ffoo%2Fbar',
            returns={'uuid': folder_uuid, 'entity_type': 'folder'}
        )
        # and it has no children
        self.register_uri(
            'https://document/service{}children/'.format(endpoint),
            returns={'count': 0}
        )

        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service{}'.format(endpoint),
            status=204
        )

        # when
        self.client.delete('/foo/bar')

        # then
        assert_that(
            httpretty.last_request(),
            has_properties(
                {'method':equal_to('DELETE'),
                 'path':equal_to('/service{}'.format(endpoint))})
        )

    def test_delete_should_delete_file_from_storage(self):
        # given
        file_uuid = 'e2c25c1b-1234-4cf6-b8d2-271e628a1256'
        endpoint = '/file/{}/'.format(file_uuid)
        # the file exists
        self.register_uri(
            'https://document/service/entity/?path=%2Ffoo%2Fbar',
            returns={'uuid': file_uuid, 'entity_type': 'file'}
        )

        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service{}'.format(endpoint),
            status=204
        )

        # when
        self.client.delete('/foo/bar')

        # then
        assert_that(
            httpretty.last_request(),
            has_properties(
                {'method':equal_to('DELETE'),
                 'path':equal_to('/service{}'.format(endpoint))})
        )



def find_sent_request(predicate):
    return next((x for x in httpretty.HTTPretty.latest_requests if predicate(x)), None)
