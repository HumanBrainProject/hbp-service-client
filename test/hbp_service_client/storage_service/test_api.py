import re
import json
import uuid
import httpretty
from hamcrest import (
    assert_that, calling, raises, equal_to, instance_of, has_entries, none)

from hbp_service_client.storage_service.api import ApiClient as AC
from hbp_service_client.storage_service.exceptions import (
    StorageException, StorageArgumentException
)

def escape_url(url):
    return re.compile(re.escape(url))

class TestApiClient(object):

    @classmethod
    def setup_class(cls):
        cls.a_uuid = str(uuid.uuid4())

    def setup_method(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({'document': {'v1': 'https://document/service'}})
        )

        self.client = AC.new('access-token')

    @staticmethod
    def teardown_method():
        httpretty.disable()
        httpretty.reset()

    def test_prep_params_ok(self):
        assert_that(
            self.client._prep_params(
                {'self': 'blah', 'foo': 'bar', 'baz': None}),
            equal_to({'foo':'bar'})
        )

    def test_prep_params_does_not_remove_empty_strings(self):
        assert_that(
            self.client._prep_params(
                {'self': 'blah', 'foo': 'bar', 'baz': ''}),
            equal_to({'foo':'bar', 'baz': ''})
        )

    #
    # Entity endpoints
    #

    def test_get_entity_details_returns_response_body(self):
        some_json = {"a": 1, "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/entity/{}/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.get_entity_details(self.a_uuid),
            equal_to(some_json)
        )

    def test_get_entity_verifies_uuids(self):
        assert_that(
            calling(self.client.get_entity_details).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_get_entity_path_extracts_path_from_response(self):
        some_json = {"path": "foobar", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/entity/{}/path/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.get_entity_path(self.a_uuid),
            equal_to("foobar")
        )

    def test_get_entity_path_verifies_uuids(self):
        assert_that(
            calling(self.client.get_entity_path).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_get_entity_collabid_extracts_id_from_response(self):
        some_json = {"collab_id": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/entity/{}/collab/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.get_entity_collab_id(self.a_uuid),
            equal_to("123456")
        )

    def test_get_entity_collab_id_verifies_uuids(self):
        assert_that(
            calling(self.client.get_entity_collab_id).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_get_entity_by_query_returns_response_body(self):
        some_json = {"collab_id": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            escape_url('https://document/service/entity/?uuid={}'.format(self.a_uuid)),
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        assert_that(
            self.client.get_entity_by_query(self.a_uuid),
            equal_to(some_json)
        )

    def test_get_entity_by_query_verifies_uuids(self):
        assert_that(
            calling(self.client.get_entity_by_query).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_get_entity_by_query_requires_params(self):
        # method raises StorageArgumentException with no args
        assert_that(
            calling(self.client.get_entity_by_query),
            raises(StorageArgumentException)
        )

    def test_get_entity_by_query_extracts_metadata(self):
        some_json = {"collab_id": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            escape_url('https://document/service/entity/?foo=bar'),
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        self.client.get_entity_by_query(metadata={'foo': 'bar'})

        # method parses metadata arg
        assert_that(
            httpretty.last_request().querystring,
            equal_to({'foo': ['bar']})  # because querystring always returns a list after the key..
        )

    #
    # Metadata endpoints
    #
    # set_metadata
    #

    def test_set_metadata_verifies_uuids(self):
        assert_that(
            calling(self.client.set_metadata).with_args(
                'entity_type', '1', {}),
            raises(StorageArgumentException)
        )

    def test_set_metadata_uses_the_right_method(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )

        self.client.set_metadata('entity_type', self.a_uuid, metadata)

        assert_that(
            httpretty.last_request().method,
            equal_to('POST')
        )

    def test_set_metadata_returns_the_response_body(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )

        assert_that(
            self.client.set_metadata('entity_type', self.a_uuid, metadata),
            equal_to(metadata)
        )

    def test_set_metadata_sets_the_right_headers(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )

        self.client.set_metadata('entity_type', self.a_uuid, metadata)

        assert_that(
            httpretty.last_request().headers,
            has_entries({'Content-Type': 'application/json'})
        )

    def test_set_metadata_checks_metadata_type(self):
        assert_that(
            calling(self.client.set_metadata).with_args(
                'entity_type',
                'entity_id',
                '{"foo": "bar"}'
            ),
            raises(StorageArgumentException),
        )

    #
    # get_metadata
    #

    def test_get_metadata_returns_the_response_body(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )
        assert_that(
            self.client.get_metadata('entity_type', self.a_uuid),
            equal_to(metadata)
        )

    def test_get_metadata_verifies_uuids(self):
        assert_that(
            calling(self.client.get_metadata).with_args(
                'entity_type', '1'),
            raises(StorageArgumentException)
        )

    #
    # update_metadata
    #

    def test_update_metadata_uses_the_right_method(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.PUT,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )

        self.client.update_metadata('entity_type', self.a_uuid, metadata)

        assert_that(
            httpretty.last_request().method,
            equal_to('PUT')
        )

    def test_update_metadata_verifies_uuids(self):
        assert_that(
            calling(self.client.update_metadata).with_args(
                'entity_type', '1', {}),
            raises(StorageArgumentException)
        )

    def test_update_metadata_returns_the_response_body(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.PUT,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )

        assert_that(
            self.client.update_metadata(
                'entity_type', self.a_uuid, metadata),
            equal_to(metadata)
        )

    def test_update_metadata_sets_the_right_headers(self):
        metadata = {'foo': 'bar'}
        httpretty.register_uri(
            httpretty.PUT,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
            body=json.dumps(metadata),
            content_type="application/json"
        )

        self.client.update_metadata('entity_type', self.a_uuid, metadata)

        assert_that(
            httpretty.last_request().headers,
            has_entries({'Content-Type': 'application/json'})
        )

    def test_update_metadata_checks_metadata_type(self):
        assert_that(
            calling(self.client.update_metadata).with_args(
                'entity_type',
                self.a_uuid,
                '{"foo": "bar"}'
            ),
            raises(StorageArgumentException),
        )

    #
    # delete_metadata
    #

    def test_delete_metadata_uses_the_right_method(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
        )

        self.client.delete_metadata(
            'entity_type', self.a_uuid, ['foo', 'bar'])

        assert_that(
            httpretty.last_request().method,
            equal_to('DELETE')
        )

    def test_delete_metadata_verifies_uuids(self):
        assert_that(
            calling(self.client.delete_metadata).with_args(
                'entity_type', '1', []),
            raises(StorageArgumentException)
        )

    def test_delete_metadata_sends_the_right_body(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/entity_type/{}/metadata/'.format(self.a_uuid),
        )

        self.client.delete_metadata(
            'entity_type', self.a_uuid, ['foo', 'bar'])

        assert_that(
            httpretty.last_request().parsed_body,
            equal_to({'keys': ['foo', 'bar']})
        )

    def test_delete_metadata_checks_metadata_type(self):
        assert_that(
            calling(self.client.delete_metadata).with_args(
                'entity_type',
                self.a_uuid,
                'i am not a list!'
            ),
            raises(StorageArgumentException)
        )

    #
    # Project endpoint
    #
    # list_projects
    #

    def test_list_projects_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/project/',
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        assert_that(
            self.client.list_projects(name='foobar', ordering='name'),
            equal_to(some_json)
        )

    def test_list_projects_sends_the_right_params(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/project/',
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        self.client.list_projects(name='foobar', ordering='name')

        assert_that(
            httpretty.last_request().querystring,
            equal_to({'name': ['foobar'], 'ordering': ['name']})
        )

    #
    # get_project_details
    #

    def test_get_project_details_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/project/{}/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.get_project_details(self.a_uuid),
            equal_to(some_json)
        )

    def test_get_project_details_verifies_uuids(self):
        assert_that(
            calling(self.client.get_project_details).with_args('1'),
            raises(StorageArgumentException)
        )

    #
    # list_project_content
    #

    def test_list_project_content_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/project/{}/children/?ordering=name'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        assert_that(
            self.client.list_project_content(self.a_uuid, ordering='name'),
            equal_to(some_json)
        )

    def test_list_project_content_verifies_uuids(self):
        assert_that(
            calling(self.client.list_project_content).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_list_project_content_send_the_right_params(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/project/{}/children/?ordering=name'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        self.client.list_project_content(self.a_uuid, ordering='name')

        assert_that(
            httpretty.last_request().querystring,
            equal_to({'ordering': ['name']})  # project_id excluded!
        )

    #
    # Create project
    #

    def test_create_project_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/project/',
            body=json.dumps(some_json),
            content_type="application/json"
        )
        assert_that(
            self.client.create_project(12345),
            equal_to(some_json)
        )

    def test_create_project_sends_the_right_body(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/project/'
        )

        self.client.create_project(12345)

        assert_that(
            httpretty.last_request().parsed_body,
            equal_to({'collab_id': 12345})
        )

    #
    # delete project
    #

    def test_delete_project_uses_the_right_method(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/project/{}/'.format(self.a_uuid),
        )

        self.client.delete_project(self.a_uuid)

        assert_that(
            httpretty.last_request().method,
            'DELETE'
        )

    def test_delete_project_verifies_uuids(self):
        assert_that(
            calling(self.client.delete_project).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_delete_project_returns_none(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/project/{}/'.format(self.a_uuid),
        )

        assert_that(
            self.client.delete_project(self.a_uuid),
            none()
        )

    #
    # Folder endpoint
    #
    # create_folder
    #

    def test_create_folder_uses_the_right_method(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/folder/',
            body=json.dumps(some_json),
            content_type="application/json"
        )

        self.client.create_folder('name', self.a_uuid)

        assert_that(
            httpretty.last_request().method,
            equal_to('POST')
        )

    def test_create_folder_verifies_uuids(self):
        assert_that(
            calling(self.client.create_folder).with_args('name', 'parent_id'),
            raises(StorageArgumentException)
        )

    def test_create_folder_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/folder/',
            body=json.dumps(some_json),
            content_type="application/json"
        )
        assert_that(
            self.client.create_folder('name', self.a_uuid),
            equal_to(some_json)
        )

    def test_create_folder_sends_the_right_body(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/folder/'
        )

        self.client.create_folder('name', self.a_uuid)

        assert_that(
            httpretty.last_request().parsed_body,
            equal_to({'name': 'name', 'parent': self.a_uuid})
        )

    #
    # get_folder
    #

    def test_get_folder_details_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/folder/{}/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.get_folder_details(self.a_uuid),
            equal_to(some_json)
        )

    def test_get_folder_details_verifies_uuids(self):
        assert_that(
            calling(self.client.get_folder_details).with_args('1'),
            raises(StorageArgumentException)
        )

    #
    # list folder_content
    #

    def test_list_folder_content_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/folder/{}/children/?ordering=name'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json",
            match_querystring=True
        )

        assert_that(
            self.client.list_folder_content(self.a_uuid, ordering='name'),
            equal_to(some_json)
        )

    def test_list_folder_content_verifies_uuids(self):
        assert_that(
            calling(self.client.list_folder_content).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_list_folder_content_sends_the_right_params(self):
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/folder/{}/children/?ordering=name'.format(self.a_uuid),
            match_querystring=True
        )

        self.client.list_folder_content(self.a_uuid, ordering='name')

        assert_that(
            httpretty.last_request().querystring,
            equal_to({'ordering': ['name']})  # folder_id excluded!
        )

    #
    # delete folder
    #

    def test_delete_folder_uses_the_right_method(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/folder/{}/'.format(self.a_uuid),
        )

        self.client.delete_folder(self.a_uuid)

        assert_that(
            httpretty.last_request().method,
            'DELETE'
        )

    def test_delete_folder_verifies_uuids(self):
        assert_that(
            calling(self.client.delete_folder).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_delete_folder_returns_none(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/folder/{}/'.format(self.a_uuid),
        )

        assert_that(
            self.client.delete_folder(self.a_uuid),
            none()
        )

    #
    # File endpoint
    #
    # create_file
    #

    def test_create_file_uses_the_right_method(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/'
        )
        self.client.create_file(
            'some_name', 'some_content_type', self.a_uuid
        )

        assert_that(
            httpretty.last_request().method,
            equal_to('POST')
        )

    def test_create_file_verifies_uuids(self):
        assert_that(
            calling(self.client.create_file).with_args(
                'some_name', 'some_content_type', 'parent_id'),
            raises(StorageArgumentException)
        )

    def test_create_file_return_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/',
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.create_file(
                'some_name', 'some_content_type', self.a_uuid
            ),
            equal_to(some_json)
        )

    def test_create_file_sends_the_right_body(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/'
        )
        self.client.create_file(
            'some_name', 'some_content_type', self.a_uuid
        )

        assert_that(
            httpretty.last_request().parsed_body,
            equal_to(
                {'name': 'some_name', 'parent': self.a_uuid,
                 'content_type': 'some_content_type'})
        )

    #
    # get_file_details
    #

    def test_get_file_details_returns_the_response_body(self):
        some_json = {"a": "123456", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        #method returns response body
        assert_that(
            self.client.get_file_details(self.a_uuid),
            equal_to(some_json)
        )

    def test_get_file_details_verifies_uuids(self):
        assert_that(
            calling(self.client.get_file_details).with_args('1'),
            raises(StorageArgumentException)
        )

    #
    # upload_file_content
    #

    def test_upload_file_content_uses_the_right_method(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(self.a_uuid),
            adding_headers={'ETag':'some_other_etag'}
        )
        self.client.upload_file_content(
            self.a_uuid, content='some_content')

        assert_that(
            httpretty.last_request().method,
            equal_to('POST')
        )

    def test_upload_file_content_verifies_uuids(self):
        assert_that(
            calling(self.client.upload_file_content).with_args(
                '1', content='content'),
            raises(StorageArgumentException)
        )

    def test_upload_file_content_sets_the_right_headers(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(self.a_uuid),
            adding_headers={'ETag':'some_other_etag'}
        )
        self.client.upload_file_content(
            self.a_uuid,
            etag='some_etag',
            content='some_content'
        )

        assert_that(
            httpretty.last_request().headers,
            has_entries({'If-Match': 'some_etag'})
        )

    def test_upload_file_content_requires_etag_in_response(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(self.a_uuid),
        )

        assert_that(
            calling(self.client.upload_file_content).with_args(
                self.a_uuid,
                etag='some_etag',
                content='some_content'
            ),
            raises(StorageException)
        )

    def test_upload_file_content_returns_the_upload_etag(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://document/service/file/{}/content/upload/'.format(self.a_uuid),
            adding_headers={'ETag':'some_other_etag'}
        )
        self.client.upload_file_content(
            self.a_uuid,
            content='some_content'
        )

        assert_that(
            self.client.upload_file_content(
                self.a_uuid,
                content='some_content'
            ),
            equal_to('some_other_etag')
        )

    #
    # copy_file_content
    #

    def test_copy_file_content_uses_the_right_method(self):
        httpretty.register_uri(httpretty.PUT, re.compile('https://.*'))
        self.client.copy_file_content(self.a_uuid, str(uuid.uuid4()))

        assert_that(
            httpretty.last_request().method,
            equal_to('PUT')
        )

    def test_copy_file_content_verifies_uuids(self):
        assert_that(
            calling(self.client.copy_file_content).with_args(
                self.a_uuid, 'source'),
            raises(StorageArgumentException)
        )

        assert_that(
            calling(self.client.copy_file_content).with_args(
                'destination', self.a_uuid),
            raises(StorageArgumentException)
        )

    def test_copy_file_content_sets_the_right_headers(self):
        httpretty.register_uri(httpretty.PUT, re.compile('https://.*'))
        self.client.copy_file_content(str(uuid.uuid4()), self.a_uuid)

        assert_that(
            httpretty.last_request().headers,
            has_entries({'X-Copy-From': self.a_uuid})
        )

    def test_copy_file_content_returns_none(self):
        httpretty.register_uri(
            httpretty.PUT,
            'https://document/service/file/{}/content/'.format(self.a_uuid)
        )

        assert_that(
            self.client.copy_file_content(self.a_uuid, str(uuid.uuid4())),
            none()
        )

    #
    # download_file_content
    #

    def test_download_file_conent_sets_the_right_headers(self):
        httpretty.register_uri(
            httpretty.GET, 'https://document/service/file/{}/content/'.format(self.a_uuid),
            adding_headers={'ETag':'some_other_etag'}
        )
        self.client.download_file_content(self.a_uuid, 'some_etag')

        assert_that(
            httpretty.last_request().headers,
            has_entries({'Accept': '*/*', 'If-None-Match': 'some_etag'})
        )

    def test_download_file_content_verifies_uuids(self):
        assert_that(
            calling(self.client.download_file_content).with_args('1'),
            raises(StorageArgumentException)
        )

    def test_download_file_content_returns_tuple(self):
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/content/'.format(self.a_uuid),
            adding_headers={'ETag':'some_etag'},
            body='somecontent'
        )

        assert_that(
            self.client.download_file_content(self.a_uuid),
            instance_of(tuple)
        )

        # Also check with status 304 for consistency
        httpretty.reset()
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/content/'.format(self.a_uuid),
            status=304,
        )

        assert_that(
            self.client.download_file_content(self.a_uuid),
            instance_of(tuple)
        )

    def test_download_file_content_requires_etag_in_response(self):
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/content/'.format(self.a_uuid),
            body='somecontent'
        )

        assert_that(
            calling(self.client.download_file_content).with_args(
                self.a_uuid),
            raises(StorageException)
        )

    def test_download_file_content_returns_the_right_content(self):
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/content/'.format(self.a_uuid),
            adding_headers={'ETag':'some_etag'},
            body='somecontent'
        )

        assert_that(
            self.client.download_file_content(self.a_uuid)[1],
            equal_to(b'somecontent')
        )

        # Also check with status 304 for consistency
        httpretty.reset()
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/content/'.format(self.a_uuid),
            status=304,
        )

        assert_that(
            self.client.download_file_content(self.a_uuid)[1],
            none()
        )

    #
    # get_signed_url
    #

    def test_get_signed_url_extracts_url_from_response_body(self):
        some_json = {"signed_url": "foo://bar", "b": [2, 3, 4], "c": {"x": "y"}}
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/file/{}/content/secure_link/'.format(self.a_uuid),
            body=json.dumps(some_json),
            content_type="application/json"
        )

        assert_that(
            self.client.get_signed_url(self.a_uuid),
            equal_to("foo://bar")
        )

    def test_get_signed_url_verifies_uuids(self):
        assert_that(
            calling(self.client.get_signed_url).with_args('1'),
            raises(StorageArgumentException)
        )

    #
    # delete_file
    #

    def test_delete_file_uses_the_right_method(self):
        httpretty.register_uri(
            httpretty.DELETE,
            'https://document/service/file/{}/'.format(self.a_uuid)
        )
        self.client.delete_file(self.a_uuid)

        assert_that(
            httpretty.last_request().method,
            equal_to('DELETE')
        )

    def test_delete_file_verifies_uuids(self):
        assert_that(
            calling(self.client.delete_file).with_args('1'),
            raises(StorageArgumentException)
        )
