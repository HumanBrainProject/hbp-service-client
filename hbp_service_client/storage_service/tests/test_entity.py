import unittest
from mock import Mock, call
import httpretty
import json
import re

from hamcrest import (assert_that, has_properties, calling, raises, equal_to)

from hbp_service_client.storage_service.exceptions import EntityArgumentException
from hbp_service_client.storage_service.entity import Entity
from hbp_service_client.client import Client

class TestEntity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Define some hard coded convenience fixtures
        cls.valid_entity_dictionary = {u'created_by': u'123456',
            u'created_on': u'2017-05-04T11:22:01.779536Z',
            u'description': u'Awesome entity',
            u'entity_type': u'folder',
            u'modified_by': u'123457',
            u'modified_on': u'2017-05-04T11:22:01.779590Z',
            u'name': u'Foo',
            u'parent': u'766cde4c-e452-49e0-a517-6ddd15c9494b',
            u'uuid': u'2e608db7-cf2e-4e5b-b4c0-4dd4063d0cab'}


    def setUp(self):
        httpretty.enable()
        # Fakes the service locator call to the services.json file
        httpretty.register_uri(
            httpretty.GET, 'https://collab.humanbrainproject.eu/services.json',
            body=json.dumps({ 'document': {'v1': 'https://document/service'} })
        )
        self.client = Client.new('access_token')

        # If set_client is broken, it will break all tests
        # Perhaps this should be somewhere else? But it's needed for all other
        # tests where we fake network calls. it would be a pain to manually do
        # this setup everywhere.
        # FIXME
        Entity.set_client(self.client)

    def tearDown(self):
        pass

    def register_uri(self, uri, returns):
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
        mydictionary = self.valid_entity_dictionary

        #when
        entity = Entity.from_dictionary(mydictionary)

        #then
        assert_that(
            entity,
            has_properties(
                {'uuid': mydictionary['uuid'],
                'name': mydictionary['name'],
                'description': mydictionary['description'],
                'children': [],
                '_path': mydictionary['name']
                })
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
        mydictionary = self.valid_entity_dictionary
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
            has_properties(
                {'uuid': mydictionary['uuid'],
                'name': mydictionary['name'],
                'description': mydictionary['description'],
                'children': [],
                '_path': mydictionary['name']
                })
        )

    #
    # parent
    #

    def test_setting_the_parent_sets_the_path(self):
        #given
        entity1 = Entity.from_dictionary(self.valid_entity_dictionary)
        entity2 = Entity.from_dictionary(self.valid_entity_dictionary)

        #when
        entity1.parent = entity2

        #then
        assert_that(
            entity1._path,
            equal_to('{}/{}'.format(entity2.name, entity1.name)))

    def test_parent_can_only_be_the_same_class(self):
        #given
        entity1 = Entity.from_dictionary(self.valid_entity_dictionary)
        entity2 = u'2e608db7-cf2e-4e5b-b4c0-4dd4063d0cab'

        #then
        assert_that(
            calling(entity1.__setattr__).with_args('parent', entity2),
            raises(ValueError))
