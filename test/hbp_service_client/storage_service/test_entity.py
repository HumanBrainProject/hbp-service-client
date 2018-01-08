import json
import re
import httpretty
import pytest
import uuid
from os.path import isfile, isdir, join
from tempfile import NamedTemporaryFile, TemporaryDirectory
from mock import Mock, call

from hamcrest import (assert_that, has_properties, has_length, calling, raises,
    contains_inanyorder, equal_to, all_of)

from hbp_service_client.storage_service.exceptions import (
    EntityArgumentException, StorageNotFoundException,
    EntityInvalidOperationException)
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
        u'name': u'Folder_A',
        u'parent': u'766cde4c-e452-49e0-a517-6ddd15c9494b',
        u'uuid': u'eac11058-4ae0-4ea9-ada8-d3ea23887509'}



    @pytest.fixture(autouse=True, scope='class')
    def init_client(self):
        httpretty.enable()
        # Block any unmocked network connection
        httpretty.HTTPretty.allow_net_connect = False
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

    @pytest.fixture(scope='class')
    def disk_tree(self):
        ''' Create a tree in the filesystem
              A      > A - folder
             /  \
            B   C    > B - folder; C - file
            |
            D        > D - file'''

        folder_a = TemporaryDirectory()
        folder_b = TemporaryDirectory(dir=folder_a.name)
        file_c = NamedTemporaryFile(dir=folder_a.name)
        file_d = NamedTemporaryFile(dir=folder_b.name)

        file_c.write(b'Hello\n')
        file_c.flush()

        file_d.write(b'World!')
        file_d.flush()

        yield {'A': folder_a, 'B': folder_b, 'C': file_c, 'D': file_d}

        file_c.close()
        file_d.close()
        folder_b.cleanup()
        folder_a.cleanup()

    @pytest.fixture
    def working_directory(self):
        '''Create a directory for downloads, then wipe it'''

        download_folder = TemporaryDirectory()

        yield download_folder

        download_folder.cleanup()


    @pytest.fixture(scope='class')
    def storage_tree(self):
        ''' A fixture to mimic the following structure in the storage service
              A      > A - folder
             /  \
            B   C    > B - folder; C - file
            |
            D        > D - file
        '''
        uuids = {
            'A': str(uuid.uuid4()),
            'B': str(uuid.uuid4()),
            'C': str(uuid.uuid4()),
            'D': str(uuid.uuid4())
        }

        contents = {
            'A': {
                u'count': 2,
                u'next': None,
                u'previous': None,
                u'results': [{
                    u'content_type': u'plain/text',
                    u'created_by': u'303447',
                    u'created_on': u'2017-03-13T10:17:01.688472Z',
                    u'description': u'This is folder B',
                    u'entity_type': u'folder',
                    u'modified_by': u'303447',
                    u'modified_on': u'2017-03-13T10:17:01.688632Z',
                    u'name': u'folder_B',
                    u'parent': uuids['A'],
                    u'uuid': uuids['B']
                }, {
                    u'content_type': u'plain/text',
                    u'created_by': u'03447',
                    u'created_on': u'2017-03-13T10:17:01.688472Z',
                    u'description': u'',
                    u'entity_type': u'file',
                    u'modified_by': u'303447',
                    u'modified_on': u'2017-03-13T10:17:01.688632Z',
                    u'name': u'file_C',
                    u'parent': uuids['A'],
                    u'uuid': uuids['C']}]},
            'B':{
                u'count': 1,
                u'next': None,
                u'previous': None,
                u'results': [{
                    u'content_type': u'plain/text',
                    u'created_by': u'303447',
                    u'created_on': u'2017-03-13T10:17:01.688472Z',
                    u'description': u'This is folder D',
                    u'entity_type': u'file',
                    u'modified_by': u'303447',
                    u'modified_on': u'2017-03-13T10:17:01.688632Z',
                    u'name': u'file_D',
                    u'parent': uuids['B'],
                    u'uuid': uuids['D']}]}}


        details = {
            'A': {
                u'collab_id': 123,
                u'created_by': u'303447',
                u'created_on': u'2017-03-10T12:50:06.077891Z',
                u'description': u'',
                u'entity_type': u'folder',
                u'modified_by': u'303447',
                u'modified_on': u'2017-03-10T12:50:06.077946Z',
                u'name': u'folder_A',
                u'uuid': uuids['A']
            },
            'C': {
                u'content_type': u'plain/text',
                u'created_by': u'03447',
                u'created_on': u'2017-03-13T10:17:01.688472Z',
                u'description': u'',
                u'entity_type': u'file',
                u'modified_by': u'303447',
                u'modified_on': u'2017-03-13T10:17:01.688632Z',
                u'name': u'file_C',
                u'uuid': uuids['C']},
            'D': {
                u'content_type': u'plain/text',
                u'created_by': u'303447',
                u'created_on': u'2017-03-13T10:17:01.688472Z',
                u'description': u'This is folder D',
                u'entity_type': u'file',
                u'modified_by': u'303447',
                u'modified_on': u'2017-03-13T10:17:01.688632Z',
                u'name': u'file_D',
                u'uuid': uuids['D']}
        }

        file_contents = {
            'C': "I am file C!",
            'D': "I am file D!"
        }

        signed_urls = {
            'C': {'signed_url': 'signed_url/C'},
            'D': {'signed_url':'signed_url/D'}
        }

        for entity in uuids:
            # Mask folder content calls
            try:
                self.register_uri(
                    'https://document/service/folder/{0}/children'.format(uuids[entity]),
                    returns=contents[entity],
                    match_query=False
                )
            except KeyError:
                # this entity has no matching data in contents, no need to mock for it
                pass

            # Mask entity detail calls
            try:
                self.register_uri(
                    'https://document/service/entity/{0}'.format(uuids[entity]),
                    returns=details[entity],
                    match_query=False
                )
            except KeyError:
                pass

            # Mask signed_url_requests
            try:
                self.register_uri(
                    'https://document/service/file/{0}/content/secure_link'.format(uuids[entity]),
                    returns=signed_urls[entity],
                    match_query=False
                )
            except KeyError:
                pass

            # Mask signed url content calls
            try:
                self.register_uri(
                    'https://document/service/{0}'.format(signed_urls[entity]['signed_url']),
                    returns=file_contents[entity],
                    match_query=False,
                )
            except KeyError:
                pass





        yield {'uuids': uuids, 'contents': contents, 'details': details}

    @staticmethod
    def register_uri(uri, returns, match_query=True, headers={}):
        httpretty.register_uri(
            httpretty.GET, re.compile(re.escape(uri)),
            match_querystring=match_query,
            body=json.dumps(returns),
            content_type="application/json",
            adding_headers=headers
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

    def test_from_disk_builds_proper_entity_from_file(self, disk_tree):
        #given
        myfile = disk_tree['C'].name

        #when
        entity = Entity.from_disk(myfile)

        #then
        assert_that(
            entity,
            has_properties({
                'name': myfile.split('/')[-1],
                'description': None,
                'children': [],
                'created_by': None,
                'modified_by': None,
                'entity_type': 'file'})
        )

    def test_from_disk_builds_proper_entity_from_directory(self, disk_tree):
        #given
        mydir = disk_tree['A'].name

        #when
        entity = Entity.from_disk(mydir)

        #then
        assert_that(
            entity,
            has_properties({
                'name': mydir.split('/')[-1],
                'description': None,
                'children': [],
                'created_by': None,
                'modified_by': None,
                'entity_type': 'folder'})
        )

    def test_from_disk_handles_paths_with_trailing_slashes(self, disk_tree):
        #given
        mydir = disk_tree['A'].name
        mypath = '{}/'.format(mydir)

        #when
        entity = Entity.from_disk(mypath)

        #then
        assert_that(
            entity,
            has_properties({
                'name': mydir.split('/')[-1],
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

    #
    # _Entity__explore_children
    #


    def test_children_are_found_from_storage(self, storage_tree):
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        entity._Entity__explore_children()

        #then
        assert_that(
            entity.children,
            has_length(2)
        )

    def test_children_are_correctly_built(self, storage_tree):
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        entity._Entity__explore_children()

        #then
        assert_that(
            entity.children[0],
            has_properties({
                'uuid': storage_tree['uuids']['B'],
                'parent': entity,
                '_path': 'folder_A/folder_B',
                'name': 'folder_B'
            })
        )

    def test_children_are_not_added_repeatedly(self, storage_tree):
        ''' Test whether repeated exploration increase the number of children'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])
        entity._Entity__explore_children()

        #when
        entity._Entity__explore_children()

        #then
        assert_that(
            entity.children,
            has_length(2)
        )

    def test_children_valid_on_browseable_only(self, storage_tree):
        '''Test whether file type entities allow exporation'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['C'])

        #then
        assert_that(
            calling(entity._Entity__explore_children),
            raises(EntityInvalidOperationException)
        )

    #
    # explore_subtree
    #

    def test_explore_subtree_from_storage(self, storage_tree):
        '''Test that not just the direct descendents are explored'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        entity.explore_subtree()

        #then
        assert_that(
            entity.children[0].children,
            has_length(1)
        )

    def test_explore_subtree_builds_entities_correctly(self, storage_tree):
        '''Test that indirect descendents are correctly built'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        entity.explore_subtree()

        #then
        assert_that(
            entity.children[0].children[0],
            has_properties({
                'uuid': storage_tree['uuids']['D'],
                'parent': entity.children[0],
                '_path': 'folder_A/folder_B/file_D',
                'name': 'file_D'
            })
        )

    def test_subtree_valid_on_all_types(self, storage_tree):
        '''Test whether file type entities allow exporation'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['C'])

        #when
        entity.explore_subtree()
        #then
        assert_that(
            entity.children,
            has_length(0)
        )

    #
    # search_subtree
    #

    def test_search_subtree_finds_results(self, storage_tree):

        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        results = entity.search_subtree('folder')

        #then
        assert_that(
            [result.name for result in results],
            contains_inanyorder('folder_A', 'folder_B')
        )

    def test_search_subtree_descendes_to_leaves(self, storage_tree):
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        results = entity.search_subtree('D')

        #then
        assert_that(
            [result.name for result in results],
            equal_to(['file_D'])
        )

    def test_search_subtree_valid_on_browseable_only(self, storage_tree):
        '''Test whether file type entities allow searching'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['C'])

        #then
        assert_that(
            calling(entity.search_subtree).with_args('foo'),
            raises(EntityInvalidOperationException)
        )

    def test_search_subtree_checks_input_is_correct_type(self, storage_tree):
        '''Test wheter an exception is raiesd with wrong argument types'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #then
        assert_that(
            calling(entity.search_subtree).with_args(123),
            raises(EntityArgumentException)
        )

    #
    # download
    #

    def test_download_creates_files_with_content(self, storage_tree, working_directory):
        '''Test that a single file can be downloaded with its contents'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['C'])

        #when
        entity.download(working_directory.name)

        #then
        with open(join(working_directory.name, 'file_C')) as file_c:
            assert_that(
                file_c.readlines(),
                equal_to(['"I am file C!"'])
            )

    def test_download_creates_directory_structure(self, storage_tree, working_directory):
        '''Test that downloading a directory recreates its subfolder structure'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])

        #when
        entity.download(working_directory.name)

        #then
        assert isfile(join(working_directory.name, 'folder_A/folder_B/file_D'))

    def test_download_can_recursively_download_folders_in_the_middle_of_the_tree(self, storage_tree, working_directory):
        '''Test that a folder can be downloaded even if it was not the root of
        exploration'''
        #given
        entity = Entity.from_uuid(storage_tree['uuids']['A'])
        entity.explore_subtree()
        folder_B = list(filter(lambda entity: entity.name == 'folder_B', entity.children))[0]

        #when
        folder_B.download(working_directory.name)

        #then
        assert isfile(join(working_directory.name, 'folder_B/file_D'))

    def test_search_results_download_correctly(self, storage_tree, working_directory):
        '''Test then downloading search results creates the correct directory
        structures for all of them'''
        #given
        prefix = working_directory.name
        entity = Entity.from_uuid(storage_tree['uuids']['A'])
        folders = entity.search_subtree('folder')
        files = entity.search_subtree('file')
        combined = folders + files

        #when
        for entity in combined:
            entity.download(prefix)

        #then
        assert_that(
            all_of(
                isfile(join(prefix, 'folder_A/folder_B/file_D')),
                isfile(join(prefix, 'folder_B/file_D')),
                isfile(join(prefix, 'file_C')),
                isfile(join(prefix, 'file_D'))
            )
        )
