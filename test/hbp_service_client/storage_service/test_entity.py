import json
import re
import httpretty
import pytest
from tempfile import NamedTemporaryFile, TemporaryDirectory
from mock import Mock, call

from hamcrest import (assert_that, has_properties, calling, raises)

from hbp_service_client.storage_service.exceptions import EntityArgumentException, StorageNotFoundException
from hbp_service_client.storage_service.entity import Entity
from hbp_service_client.storage_service.api import ApiClient

class TestEntity(object):

    # Define some hard coded convenience fixtures
    VALID_ENTITY_DICTIONARY = {
        u'created_by': u'123456',
        u'created_on': u'2017-05-04T11:22:01.779536Z',
        u'description': u'Awesome entity',
        u'entity_type': u'folder',
        u'modified_by': u'123457',
        u'modified_on': u'2017-05-04T11:22:01.779590Z',
        u'name': u'Foo',
        u'parent': u'766cde4c-e452-49e0-a517-6ddd15c9494b',
        u'uuid': u'2e608db7-cf2e-4e5b-b4c0-4dd4063d0cab'}



    @pytest.fixture(autouse=True, scope='class')
    def init_client(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({'document': {'v1': 'https://document/service'}})
        )
        self.client = ApiClient.new('access_token')

        # If set_client is broken, it will break all tests
        # Perhaps this should be somewhere else? But it's needed for all other
        # tests where we fake network calls. it would be a pain to manually do
        # this setup everywhere.
        # FIXME
        Entity.set_client(self.client)

    @staticmethod
    def register_uri(uri, returns):
        httpretty.register_uri(
            httpretty.GET, re.compile(re.escape(uri)),
            match_querystring=True,
            body=json.dumps(returns),
            content_type="application/json"
        )

    #
    # from_dictionary
    #

    def test_from_dictionary_builds_proper_entity_from_valid_dict(self):
        #given
        mydictionary = self.VALID_ENTITY_DICTIONARY

        #when
        entity = Entity.from_dictionary(mydictionary)

        #then
        assert_that(
            entity,
            has_properties({
                'uuid': mydictionary['uuid'],
                'name': mydictionary['name'],
                'description': mydictionary['description'],
                'children': [],
                '_path': mydictionary['name']})
        )

    def test_from_dictionary_raises_exception_for_invalid_argument(self):
        #given
        mydictionary = "foo"

        #then
        assert_that(
            calling(Entity.from_dictionary).with_args(mydictionary),
            raises(EntityArgumentException))

    #
    # from_uuid
    #

    def test_from_uuid_builds_proper_entity_from_valid_uuid(self):
        #given
        mydictionary = self.VALID_ENTITY_DICTIONARY
        myuuid = mydictionary['uuid']
        self.register_uri(
            'https://document/service/entity/{0}'.format(myuuid),
            returns=mydictionary
        )

        #when
        entity = Entity.from_uuid(myuuid)

        #then
        assert_that(
            entity,
            has_properties({
                'uuid': mydictionary['uuid'],
                'name': mydictionary['name'],
                'description': mydictionary['description'],
                'children': [],
                '_path': mydictionary['name']})
        )

    def test_from_uuid_raises_exception_for_notfoud_uuid(self):
        #given
        missing_uuid = '2ddb5666-a0a7-439a-8653-68c825a0b483'
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/entity/{0}/'.format(missing_uuid),
            status=404)

        #then
        assert_that(
            calling(Entity.from_uuid).with_args(missing_uuid),
            raises(StorageNotFoundException)
        )

    def test_from_uuid_raises_exception_for_invalid_parameter(self):
        #given
        missing_uuid = 'foo'
        httpretty.register_uri(
            httpretty.GET,
            'https://document/service/entity/{0}/'.format(missing_uuid),
            status=404)

        #then
        assert_that(
            calling(Entity.from_uuid).with_args(missing_uuid),
            raises(EntityArgumentException)
        )


    #
    # from_disk
    #

    def test_from_disk_builds_proper_entity_from_file(self):
        #given
        myfile = NamedTemporaryFile()

        #when
        entity = Entity.from_disk(myfile.name)
        myfile.close()

        #then
        assert_that(
            entity,
            has_properties({
                'name': myfile.name.split('/')[-1],
                'description': None,
                'children': [],
                'created_by': None,
                'modified_by': None,
                'entity_type': 'file'})
        )

    def test_from_disk_builds_proper_entity_from_directory(self):
        #given
        mydir = TemporaryDirectory()

        #when
        entity = Entity.from_disk(mydir.name)
        mydir.cleanup()

        #then
        assert_that(
            entity,
            has_properties({
                'name': mydir.name.split('/')[-1],
                'description': None,
                'children': [],
                'created_by': None,
                'modified_by': None,
                'entity_type': 'folder'})
        )

    def test_from_disk_handles_paths_with_trailing_slashes(self):
        #given
        mydir = TemporaryDirectory()
        mypath = '{}/'.format(mydir.name)

        #when
        entity = Entity.from_disk(mypath)

        #then
        assert_that(
            entity,
            has_properties({
                'name': mydir.name.split('/')[-1],
                'description': None,
                'children': [],
                'created_by': None,
                'modified_by': None,
                'entity_type': 'folder'})
        )

    def test_from_disk_only_accepts_absolute_paths(self):
        #then
        assert_that(
            calling(Entity.from_disk).with_args('./idontexist'),
            raises(EntityArgumentException)
        )


    def test_from_disk_raises_exception_for_invalid_path(self):
        #then
        assert_that(
            calling(Entity.from_disk).with_args('/idontexist'),
            raises(EntityArgumentException)
        )
