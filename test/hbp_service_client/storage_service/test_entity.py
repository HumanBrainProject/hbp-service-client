import json
import re
import responses
import pytest
import uuid

from os.path import isfile, isdir, join, basename
from os import mkdir
from mock import Mock, call
from tempfile import NamedTemporaryFile
try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory

from hamcrest import (
    assert_that, has_properties, has_length, calling, raises, not_none,
    contains, contains_inanyorder, equal_to, has_entry, has_entries, matches_regexp)

from hbp_service_client.storage_service.exceptions import (
    EntityArgumentException, StorageNotFoundException,
    EntityInvalidOperationException, EntityDownloadException, EntityUploadException)
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
    MISSING_UUID = '999cfed5-315a-4823-83fb-4c5ecddc3870'
    __UUIDS = {
        'A': str(uuid.uuid4()),
        'B': str(uuid.uuid4()),
        'C': str(uuid.uuid4()),
        'D': str(uuid.uuid4()),
        'U': str(uuid.uuid4())}
    __CONTENTS = {
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
                u'parent': __UUIDS['A'],
                u'uuid': __UUIDS['B']
            }, {
                u'content_type': u'plain/text',
                u'created_by': u'03447',
                u'created_on': u'2017-03-13T10:17:01.688472Z',
                u'description': u'',
                u'entity_type': u'file',
                u'modified_by': u'303447',
                u'modified_on': u'2017-03-13T10:17:01.688632Z',
                u'name': u'file_C',
                u'parent': __UUIDS['A'],
                u'uuid': __UUIDS['C']}]},
        'B': {
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
                u'parent': __UUIDS['B'],
                u'uuid': __UUIDS['D']}]},
        'U': {
            u'count': 0,
            u'next': None,
            u'previous': None,
            u'results': []}}
    __DETAILS = {
        'A': {
            u'collab_id': 123,
            u'created_by': u'303447',
            u'created_on': u'2017-03-10T12:50:06.077891Z',
            u'description': u'',
            u'entity_type': u'folder',
            u'modified_by': u'303447',
            u'modified_on': u'2017-03-10T12:50:06.077946Z',
            u'name': u'folder_A',
            u'uuid': __UUIDS['A']
        },
        'B': {
            u'created_by': u'303447',
            u'created_on': u'2017-03-13T10:17:01.688472Z',
            u'description': u'This is folder B',
            u'entity_type': u'folder',
            u'modified_by': u'303447',
            u'modified_on': u'2017-03-13T10:17:01.688632Z',
            u'name': u'folder_B',
            u'uuid': __UUIDS['B']
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
            u'uuid': __UUIDS['C']},
        'D': {
            u'content_type': u'plain/text',
            u'created_by': u'303447',
            u'created_on': u'2017-03-13T10:17:01.688472Z',
            u'description': u'This is folder D',
            u'entity_type': u'file',
            u'modified_by': u'303447',
            u'modified_on': u'2017-03-13T10:17:01.688632Z',
            u'name': u'file_D',
            u'uuid': __UUIDS['D']},
        'U': {
            u'collab_id': 123,
            u'created_by': u'303447',
            u'created_on': u'2017-03-10T12:50:06.077891Z',
            u'description': u'',
            u'entity_type': u'folder',
            u'modified_by': u'303447',
            u'modified_on': u'2017-03-10T12:50:06.077946Z',
            u'name': u'folder_U',
            u'uuid': __UUIDS['U']}
        }
    __FILE_CONTENTS = {
        'C': "I am file C!",
        'D': "I am file D!"}
    __SIGNED_URLS = {
        'C': {'signed_url': 'signed_url/C/'},
        'D': {'signed_url': 'signed_url/D/'}}

    ''' A fixture to mimic the following structure in the storage service
          A    U > A - folder, U - empty folder
         /  \
        B   C    > B - folder; C - file
        |
        D        > D - file
    '''
    STORAGE_TREE = {
        'uuids': __UUIDS,
        'contents': __CONTENTS,
        'details': __DETAILS,
        'file_contents': __FILE_CONTENTS,
        'signed_urls': __SIGNED_URLS}

    @staticmethod
    def register_uri(uri, returns=None, match_query=True, method='GET', **kwargs):
        responses.add(
            method=method,
            url=uri,
            match_querystring=match_query,
            json=returns,
            **kwargs
        )

    @pytest.fixture(autouse=True)
    def fake_network(self):
        responses.start()

        # Config
        self.register_uri(
            'https://collab.humanbrainproject.eu/services.json',
            returns={'document': {'v1': 'https://document/service'}})

        self.client = ApiClient.new('access_token')
        Entity.set_client(self.client)

        # 404 on uuid details
        self.register_uri(
            'https://document/service/entity/{}/'.format(self.MISSING_UUID),
            status=404)

        # 404 on path search
        self.register_uri(
            'https://document/service/entity/?path=%2Fidont%2Fexist',
            status=404)

        # Searches

        self.register_uri(
            'https://document/service/entity/?uuid={}'.format(self.STORAGE_TREE['uuids']['A']),
            returns=self.STORAGE_TREE['details']['A'])

        self.register_uri(
            'https://document/service/entity/?uuid={}'.format(self.STORAGE_TREE['uuids']['U']),
            returns=self.STORAGE_TREE['details']['U'])

        self.register_uri(
            'https://document/service/entity/?path=%2F123%2Ffolder_A',
            returns=self.STORAGE_TREE['details']['A'])

        self.register_uri(
            'https://document/service/entity/?path=%2F123%2Ffolder_A%2Ffile_C',
            returns=self.STORAGE_TREE['details']['C'])

        # Uploads (POST)

        self.register_uri(
            re.compile(re.escape('https://document/service/file/')),
            returns=self.STORAGE_TREE['details']['C'],
            method='POST',
            headers={'ETag': 'someetag'})

        self.register_uri(
            'https://document/service/folder/',
            returns=self.STORAGE_TREE['details']['B'],
            method='POST')

        # Entity details

        for entity in self.STORAGE_TREE['uuids']:
            # Mask folder content calls
            try:
                self.register_uri(
                    'https://document/service/folder/{0}/children/?ordering=name&page=1'.format(
                        self.STORAGE_TREE['uuids'][entity]),
                    returns=self.STORAGE_TREE['contents'][entity],
                    match_query=True
                )
            except KeyError:
                # this entity has no matching data in contents, no need to mock for it
                pass

            # Mask entity detail calls
            try:
                self.register_uri(
                    'https://document/service/entity/{0}/'.format(
                        self.STORAGE_TREE['uuids'][entity]),
                    returns=self.STORAGE_TREE['details'][entity],
                    match_query=False
                )
            except KeyError:
                pass

            # Mask signed_url_requests
            try:
                self.register_uri(
                    'https://document/service/file/{0}/content/secure_link/'.format(
                        self.STORAGE_TREE['uuids'][entity]),
                    returns=self.STORAGE_TREE['signed_urls'][entity]
                )
            except KeyError:
                pass

            # Mask signed url content calls
            try:
                self.register_uri(
                    'https://document/service/{0}'.format(
                        self.STORAGE_TREE['signed_urls'][entity]['signed_url']),
                    returns=self.STORAGE_TREE['file_contents'][entity]
                )
            except KeyError:
                pass

        yield
        responses.stop()

    @pytest.fixture(scope='class')
    def disk_tree(self):
        ''' Create a tree in the filesystem
              A      > A - folder
             /  \
            B   C    > B - folder; C - file
            |\
            D E       > D - file; E - file'''

        folder_a = TemporaryDirectory(prefix='folder_')
        folder_b = TemporaryDirectory(prefix='folder_', dir=folder_a.name)
        file_c = NamedTemporaryFile(dir=folder_a.name, prefix="file_", suffix=".txt")
        file_d = NamedTemporaryFile(dir=folder_b.name, prefix="file_", suffix=".ipynb")
        file_e = NamedTemporaryFile(dir=folder_b.name, prefix="file_")

        file_c.write(b'Hello\n')
        file_c.flush()

        file_d.write(b'World!')
        file_d.flush()

        file_e.write(b'Foo')
        file_e.flush

        yield {'A': folder_a, 'B': folder_b, 'C': file_c, 'D': file_d, 'E': file_e}

        file_c.close()
        file_d.close()
        file_e.close()
        folder_b.cleanup()
        folder_a.cleanup()

    @pytest.fixture(scope='class')
    def disk_tree_with_unicode(self):
        ''' Create a tree in the filesystem
              A         > A - folder
              |
              e-acute   > b - file
        '''

        folder_a = TemporaryDirectory()
        file_b = NamedTemporaryFile(dir=folder_a.name, prefix=u'\xe9', suffix=".txt")

        file_b.write(b'Hello\n')
        file_b.flush()

        yield {'A': folder_a, 'B': file_b}

        file_b.close()
        folder_a.cleanup()

    @pytest.fixture
    def working_directory(self):
        '''Create a directory for downloads, then wipe it'''

        download_folder = TemporaryDirectory()

        yield download_folder

        download_folder.cleanup()

    #
    # from_dictionary
    #

    def test_from_dictionary_builds_proper_entity_from_valid_dict(self):
        # given
        mydictionary = self.VALID_ENTITY_DICTIONARY

        # when
        entity = Entity.from_dictionary(mydictionary)

        # then
        assert_that(
            entity,
            has_properties({
                'uuid': mydictionary['uuid'],
                'name': mydictionary['name'],
                'description': mydictionary['description'],
                'children': []})
        )

    def test_from_dictionary_raises_exception_for_invalid_argument(self):
        # given
        mydictionary = "foo"

        # then
        assert_that(
            calling(Entity.from_dictionary).with_args(mydictionary),
            raises(EntityArgumentException))

    #
    # from_uuid
    #

    def test_from_uuid_builds_proper_entity_from_valid_uuid(self):
        # given
        myuuid = self.STORAGE_TREE['uuids']['A']

        # when
        entity = Entity.from_uuid(myuuid)

        # then
        assert_that(
            entity,
            has_properties({
                'uuid': myuuid,
                'name': self.STORAGE_TREE['details']['A']['name'],
                'description': self.STORAGE_TREE['details']['A']['description'],
                'children': []})
        )

    def test_from_uuid_saves_content_type_from_files(self):
        # given
        myuuid = self.STORAGE_TREE['uuids']['C']

        # when
        entity = Entity.from_uuid(myuuid)

        # then
        assert_that(
            entity,
            has_properties({
                'content_type': self.STORAGE_TREE['details']['C']['content_type']})
        )

    def test_from_uuid_raises_exception_for_notfoud_uuid(self):
        # given
        missing_uuid = self.MISSING_UUID

        # then
        assert_that(
            calling(Entity.from_uuid).with_args(missing_uuid),
            raises(StorageNotFoundException)
        )

    def test_from_uuid_raises_exception_for_invalid_parameter(self):
        # given
        invalid_uuid = 'foo'

        # then
        assert_that(
            calling(Entity.from_uuid).with_args(invalid_uuid),
            raises(EntityArgumentException)
        )

    #
    # from_path
    #

    def test_from_path_builds_proper_entity_from_valid_path(self):
        # given
        mydictionary = self.STORAGE_TREE['details']['A']
        mypath = '/123/folder_A'

        # when
        entity = Entity.from_path(mypath)

        # then
        assert_that(
            entity,
            has_properties({
                'uuid': mydictionary['uuid'],
                'name': mydictionary['name'],
                'description': mydictionary['description'],
                'children': []})
        )

    def test_from_path_saves_content_type_from_files(self):
        # given
        mypath = '/123/folder_A/file_C'

        # when
        entity = Entity.from_path(mypath)

        # then
        assert_that(
            entity,
            has_properties({
                'content_type': self.STORAGE_TREE['details']['C']['content_type']})
        )

    def test_from_path_raises_exception_for_notfoud_path(self):
        # given
        missing_path = '/idont/exist'

        # then
        assert_that(
            calling(Entity.from_path).with_args(missing_path),
            raises(StorageNotFoundException)
        )

    # #
    # # from_disk
    # #
    #
    # def test_from_disk_builds_proper_entity_from_file(self, disk_tree):
    #     # given
    #     myfile = disk_tree['C'].name
    #
    #     # when
    #     entity = Entity.from_disk(myfile)
    #
    #     # then
    #     assert_that(
    #         entity,
    #         has_properties({
    #             'name': myfile.split('/')[-1],
    #             'description': None,
    #             'children': [],
    #             'created_by': None,
    #             'modified_by': None,
    #             'entity_type': 'file'})
    #     )
    #
    # def test_from_disk_builds_proper_entity_from_directory(self, disk_tree):
    #     # given
    #     mydir = disk_tree['A'].name
    #
    #     # when
    #     entity = Entity.from_disk(mydir)
    #
    #     # then
    #     assert_that(
    #         entity,
    #         has_properties({
    #             'name': mydir.split('/')[-1],
    #             'description': None,
    #             'children': [],
    #             'created_by': None,
    #             'modified_by': None,
    #             'entity_type': 'folder'})
    #     )
    #
    # def test_from_disk_handles_paths_with_trailing_slashes(self, disk_tree):
    #     # given
    #     mydir = disk_tree['A'].name
    #     mypath = '{}/'.format(mydir)
    #
    #     # when
    #     entity = Entity.from_disk(mypath)
    #
    #     # then
    #     assert_that(
    #         entity,
    #         has_properties({
    #             'name': mydir.split('/')[-1],
    #             'description': None,
    #             'children': [],
    #             'created_by': None,
    #             'modified_by': None,
    #             'entity_type': 'folder'})
    #     )
    #
    # def test_from_disk_fill_content_type_for_files(self, disk_tree):
    #     '''Test whether content type is guessed for files'''
    #     # given
    #     myfile = disk_tree['C'].name
    #
    #     # when
    #     entity = Entity.from_disk(myfile)
    #
    #     # then
    #     assert_that(
    #         entity,
    #         has_properties({
    #             'content_type': not_none()})
    #     )
    #
    # def test_from_disk_recognizes_notebook_content_type_for_files(self, disk_tree):
    #     '''Test whether content type is guessed for files'''
    #     # given
    #     myfile = disk_tree['D'].name
    #
    #     # when
    #     entity = Entity.from_disk(myfile)
    #
    #     # then
    #     assert_that(
    #         entity,
    #         has_properties({
    #             'content_type': 'application/x-ipynb+json'})
    #     )
    #
    # def test_from_disk_only_accepts_absolute_paths(self):
    #     # then
    #     assert_that(
    #         calling(Entity.from_disk).with_args('./idontexist'),
    #         raises(EntityArgumentException)
    #     )
    #
    # def test_from_disk_raises_exception_for_invalid_path(self):
    #     # then
    #     assert_that(
    #         calling(Entity.from_disk).with_args('/idontexist'),
    #         raises(EntityArgumentException)
    #     )
    #
    # def test_from_disk_accepts_unicode_paths(self, disk_tree_with_unicode):
    #     # given
    #     myfile = u'{}'.format(disk_tree_with_unicode['B'].name)
    #
    #     # when
    #     entity = Entity.from_disk(myfile)
    #
    #     # then
    #     assert_that(
    #         entity,
    #         has_properties({
    #             'name': myfile.split('/')[-1],
    #             'description': None,
    #             'children': [],
    #             'created_by': None,
    #             'modified_by': None,
    #             'entity_type': 'file'})
    #     )

    #
    # explore_children
    #

    def test_children_are_found_from_storage(self):
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        entity.explore_children()

        # then
        assert_that(
            entity.children,
            has_length(2)
        )

    # def test_children_are_found_from_disk(self, disk_tree):
    #     '''Test exploration also works on disk'''
    #     # given
    #     entity = Entity.from_disk(disk_tree['A'].name)
    #
    #     # when
    #     entity.explore_children()
    #
    #     # then
    #     assert_that(
    #         [ent.name for ent in entity.children],
    #         contains_inanyorder(
    #             basename(disk_tree['B'].name),
    #             basename(disk_tree['C'].name))
    #     )

    def test_children_are_correctly_built_from_storage(self):
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        entity.explore_children()

        # then
        assert_that(
            entity.children[0],
            has_properties({
                'uuid': self.STORAGE_TREE['uuids']['B'],
                'parent': entity,
                'name': 'folder_B'
            })
        )

    # def test_children_are_correctly_built_from_disk(self, disk_tree):
    #     # given
    #     entity = Entity.from_disk(disk_tree['B'].name)
    #
    #     # when
    #     entity.explore_children()
    #
    #     # then
    #     assert_that(
    #         entity.children,
    #         contains_inanyorder(
    #             has_properties({
    #                 'uuid': None,
    #                 'parent': entity,
    #                 'entity_type': 'file',
    #                 'name': basename(disk_tree['D'].name)}),
    #             has_properties({
    #                 'uuid': None,
    #                 'parent': entity,
    #                 'entity_type': 'file',
    #                 'name': basename(disk_tree['E'].name)}))
    #     )

    def test_children_are_not_added_repeatedly_from_storage(self):
        ''' Test whether repeated exploration increase the number of children'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])
        entity.explore_children()

        # when
        entity.explore_children()

        # then
        assert_that(
            entity.children,
            has_length(2)
        )

    # def test_children_are_not_added_repeatedly_from_disk(self, disk_tree):
    #     ''' Test whether repeated exploration increase the number of children'''
    #     # given
    #     entity = Entity.from_disk(disk_tree['A'].name)
    #     entity.explore_children()
    #
    #     # when
    #     entity.explore_children()
    #
    #     # then
    #     assert_that(
    #         entity.children,
    #         has_length(2)
    #     )

    def test_children_valid_on_browseable_only_from_storage(self):
        '''Test whether file type entities allow exploration'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])

        # then
        assert_that(
            calling(entity.explore_children),
            raises(EntityInvalidOperationException)
        )

    #
    # explore_subtree
    #

    def test_explore_subtree_from_storage(self):
        '''Test that not just the direct descendents are explored'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        entity.explore_subtree()

        # then
        assert_that(
            entity.children[0].children,
            has_length(1)
        )

    def test_explore_subtree_builds_entities_correctly(self):
        '''Test that indirect descendents are correctly built'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        entity.explore_subtree()

        # then
        assert_that(
            entity.children[0].children[0],
            has_properties({
                'uuid': self.STORAGE_TREE['uuids']['D'],
                'parent': entity.children[0],
                'name': 'file_D'
            })
        )

    def test_subtree_valid_on_all_types(self):
        '''Test whether file type entities allow exporation'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])

        # when
        entity.explore_subtree()
        # then
        assert_that(
            entity.children,
            has_length(0)
        )

    #
    # search_subtree
    #

    def test_search_subtree_finds_results(self):

        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        results = entity.search_subtree('folder')

        # then
        assert_that(
            [result.name for result in results],
            contains_inanyorder('folder_A', 'folder_B')
        )

    def test_search_subtree_descendes_to_leaves(self):
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        results = entity.search_subtree('D')

        # then
        assert_that(
            [result.name for result in results],
            equal_to(['file_D'])
        )

    def test_search_subtree_valid_on_browseable_only(self):
        '''Test whether file type entities allow searching'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])

        # then
        assert_that(
            calling(entity.search_subtree).with_args('foo'),
            raises(EntityInvalidOperationException)
        )

    def test_search_subtree_checks_input_is_correct_type(self):
        '''Test wheter an exception is raiesd with wrong argument types'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # then
        assert_that(
            calling(entity.search_subtree).with_args(123),
            raises(EntityArgumentException)
        )

    # def test_search_works_on_entities_created_from_disk(self, disk_tree):
    #     '''Test whether it is possible to search in a tree contructed from the disk'''
    #     # given
    #     entity = Entity.from_disk(disk_tree["A"].name)
    #
    #     # when
    #     results = entity.search_subtree('file')
    #
    #     # then
    #     assert_that(
    #         [result.name for result in results],
    #         contains_inanyorder(basename(disk_tree['C'].name), basename(disk_tree['D'].name),
    #                 basename(disk_tree['E'].name))
    #     )

    #
    # download
    #

    def test_download_creates_files_with_content(self, working_directory):
        '''Test that a single file can be downloaded with its contents'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])

        # when
        entity.download(working_directory.name)

        # then
        with open(join(working_directory.name, 'file_C')) as file_c:
            assert_that(
                file_c.readlines(),
                equal_to(['"I am file C!"'])
            )

    def test_download_creates_directory_structure(self, working_directory):
        '''Test that downloading a directory recreates its subfolder structure'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # when
        entity.download(working_directory.name)

        # then
        assert isfile(join(working_directory.name, 'folder_A/folder_B/file_D'))

    def test_download_can_recursively_download_folders_in_the_middle_of_the_tree(self, working_directory):
        '''Test that a folder can be downloaded even if it was not the root of
        exploration'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])
        entity.explore_subtree()
        folder_B = list(filter(lambda entity: entity.name == 'folder_B', entity.children))[0]

        # when
        folder_B.download(working_directory.name)

        # then
        assert isfile(join(working_directory.name, 'folder_B/file_D'))

    def test_search_results_download_correctly(self, working_directory):
        '''Test then downloading search results creates the correct directory
        structures for all of them'''
        # given
        prefix = working_directory.name
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])
        folders = entity.search_subtree('folder')
        files = entity.search_subtree('file')
        combined = folders + files

        # when
        for entity in combined:
            entity.download(prefix)

        # then
        assert(
            isfile(join(prefix, 'folder_A/folder_B/file_D')) and
            isfile(join(prefix, 'folder_B/file_D')) and
            isfile(join(prefix, 'file_C')) and
            isfile(join(prefix, 'file_D'))
        )

    def test_download_fails_if_files_already_exist(self, working_directory):
        '''Test that the method does not overwrite content but rather fails'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])
        open(join(working_directory.name, 'file_C'), 'a').close()

        # then
        assert_that(
            calling(entity.download).with_args(working_directory.name),
            raises(OSError)
        )

    def test_download_fails_if_folder_already_exists(self, working_directory):
        '''Test the method does not try to download into already existing folders'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])
        mkdir(join(working_directory.name, 'folder_A'))

        # then
        assert_that(
            calling(entity.download).with_args(working_directory.name),
            raises(OSError)
        )

    def test_download_fails_when_target_dir_is_missing(self):
        '''Test the method raising an error when the destination folder is missing'''

        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['A'])

        # then
        assert_that(
            calling(entity.download).with_args('/idontexist'),
            raises(OSError)
        )

    def test_entities_download_to_different_directories(self, working_directory):
        '''Test that entities can be downloaded to mulitple directories in
            sequence without being re-initialized.'''
        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])
        entity.download(working_directory.name)
        new_work_dir = TemporaryDirectory()

        # when
        entity.download(new_work_dir.name)

        # then
        with open(join(new_work_dir.name, 'file_C')) as file_c:
            assert_that(
                file_c.readlines(),
                equal_to(['"I am file C!"'])
            )
        new_work_dir.cleanup()

    #
    # upload
    #
    @pytest.fixture
    def fake_destination_check(self, request):
        '''A fixture that fakes the content count when checking the upload destination.
        It can accept parameters from the test function to alter the request/response
        for a given file_name and count'''

        fake_content_count = {
            u'count': getattr(request.function, 'fake_count', 0),
            u'next': None,
            u'previous': None,
            u'results': []}
        fake_contents = responses.Response(
            method='GET',
            url=re.compile(r'https://document/service/folder/[\w\-]+/children/\?name={}'.format(
                request.function.entity_name)),
            match_querystring=True,
            json=fake_content_count)
        responses.add(fake_contents)
        yield

        responses.remove(fake_content_count)

    # def test_upload_only_valid_on_folders(self):
    #     '''Test that files cannot be used to upload destination'''
    #     # given
    #     entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['C'])
    #
    #     # then
    #     assert_that(
    #         calling(entity.upload).with_args('/foo'),
    #         raises(EntityInvalidOperationException)
    #     )
    #
    # def test_upload_checks_the_path(self):
    #     # given
    #     entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['U'])
    #
    #     # then
    #     assert_that(
    #         calling(entity.upload).with_args('/idont/exist'),
    #         raises(EntityArgumentException)
    #     )


    def test_upload_checks_destinations_children(self, disk_tree, fake_destination_check):
        '''Test that the upload raises an Exception if the destination parent entity
        already has an entity with the same name as we're about to upload.
        This is simmetric with the download behavior where we do not overwrite
        files and folders.'''
        # set fake destination check
        fake_count = 1  # no entity with such name exists at the destinations
        entity_name = basename(disk_tree['E'].name)  # when checked with this name

        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['U'])

        # then
        assert_that(
            calling(entity.upload).with_args(disk_tree['E'].name),
            raises(EntityUploadException)
        )
        responses.remove(fake_contents)


    def test_upload_creates_file_in_storage(self, disk_tree, fake_destination_check):
        '''Test whether a single file is created in the storage service'''
        # set fake destination check
        fake_count = 0  # no entity with such name exists at the destinations
        entity_name = basename(disk_tree['C'].name)  # when checked with this name

        # given
        entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['U'])

        # when
        entity.upload(disk_tree['C'].name)
        last_two_requests = [response.request for response in responses.calls[-2:]]

        # then
        assert_that(
            last_two_requests,
            contains(
                # 1st call is create entity
                has_properties({
                    'method': 'POST',
                    'path_url': '/service/file/'}),
                # 2nd call is to upload content
                has_properties(
                    method='POST',
                    path_url=matches_regexp(r'/service/file/[\w\-]+/content/upload/')))
        )

    #
    # def test_upload_guesses_the_mimetype(self, disk_tree):
    #     '''Test whether the mimetype is guessed for an uploaded file'''
    #     # given
    #     entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['U'])
    #
    #     # when
    #     entity.upload(disk_tree['C'].name)
    #     last_two_requests = [response.request for response in responses.calls[-2:]]
    #     # then
    #     assert_that(
    #         json.loads(last_two_requests[0].body.decode('utf-8')),
    #         has_entries("content_type", "text/plain")
    #     )
    #
    # def test_upload_does_not_send_empty_mimetype(self, disk_tree):
    #     '''Test whether the mimetype is guessed for an uploaded file'''
    #     # given
    #     entity = Entity.from_uuid(self.STORAGE_TREE['uuids']['U'])
    #
    #     # when
    #     entity.upload(disk_tree['E'].name)
    #     last_two_requests = [response.request for response in responses.calls[-2:]]
    #
    #     # then
    #     assert_that(
    #         json.loads(last_two_requests[0].body.decode('utf-8')),
    #         has_entry('content_type', 'application/octet-stream')
    #     )
    #
    # def test_upload_processes_directories_in_storage(self, disk_tree):
    #     '''Test whether a single directory is created in the storage service'''
    #     # given
    #     entity = Entity.from_disk(disk_tree['B'].name)
    #
    #     # when
    #     a_uuid = self.STORAGE_TREE['uuids']['U']
    #
    #     entity.upload(destination_uuid=a_uuid)
    #     last_five_requests = [response.request for response in responses.calls[-5:]]
    #     # then
    #     assert_that(
    #         last_five_requests,
    #         contains(
    #             # 1st call is create directory
    #             has_properties({
    #                 'method': 'POST',
    #                 'path_url': '/service/folder/'}),
    #             # 2nd call is create file D
    #             has_properties({
    #                 'method': 'POST',
    #                 'path_url': '/service/file/'}),
    #             # 3rd call is upload file content
    #             has_properties({
    #                 'method': 'POST',
    #                 'path_url': matches_regexp(r'/service/file/[\w\-]+/content/upload/')}),
    #             # 4th call is create file E
    #             has_properties({
    #                 'method': 'POST',
    #                 'path_url': '/service/file/'}),
    #             # 3rd call is upload file content
    #             has_properties({
    #                 'method': 'POST',
    #                 'path_url': matches_regexp(r'/service/file/[\w\-]+/content/upload/')}))
    #     )
    #
