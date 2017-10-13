from os import (mkdir, listdir)
from os.path import (exists, isdir, isfile, basename, join)
from hbp_service_client.storage_service.api import ApiClient
from hbp_service_client.storage_service.exceptions import EntityArgumentException

class Entity(object):

    _SUBTREE_TYPES = ['project', 'folder']
    __client = None

    def __init__(self, entity_type, uuid, name, description):
        self.entity_type = entity_type
        self.uuid = uuid
        self.name = name
        self.description = description
        self.children = []
        # _path is always relative to the root of the tree
        # in the root it's the entity name
        self._path = name
        self.__disk_path = None

    @classmethod
    def set_client(cls, client):
        # #verify the interface
        # if (not hasattr(client, 'storage') and
        #         hasattr(client.storage, 'list_folder_content') and
        #         callable(client.storage.list_folder_content)):
        #     raise ValueError('The client is of invalid specifications')
        if not isinstance(client, ApiClient):
            raise ValueError('The client is of invalid specifications')
        cls.__client = client

    @classmethod
    def from_dictionary(cls, dictionary):
        try:
            return cls(
                entity_type=dictionary['entity_type'],
                uuid=dictionary['uuid'],
                name=dictionary['name'],
                description=dictionary['description'])
        except (TypeError, KeyError) as exc:
            raise EntityArgumentException(exc)

    @classmethod
    def from_uuid(cls, uuid):
        if not cls.__client:
            raise Exception('This method requires a client set')
        # TODO exception handling
        return cls.from_dictionary(cls.__client.get_entity_details(uuid))

    @classmethod
    def from_disk(cls, path):
        ''' Create an entity from the disk
        '''
        if not exists(path):
            raise EntityArgumentException('The given path does not exist on the disk.')

        entity_dict = {
            'uuid': None,
            'description': None,
            'name': basename(path)} # TODO check basename of /tmp/a/
        if isdir(path):
            entity_dict['entity_type'] = 'folder'
        elif isfile(path):
            entity_dict['entity_type'] = 'file'
        else:
            raise EntityArgumentException('Links are not supported.')

        entity = cls.from_dictionary(**entity_dict)
        entity.__disk_path = path
        return entity

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        if not isinstance(parent, type(self)):
            raise ValueError("Parent must be of type {0}", type(self))
        self._parent = parent
        # if it has a parent, it's under it in the path
        self._path = '{0}/{1}'.format(parent._path, self.name)

    def __str__(self):
        return "({id}: {name}[{type}])".format(
            id=self.uuid, name=self.name, type=self.entity_type)

    def __repr__(self):
        return self.__str__()

    def explore_children(self):
        if not self.entity_type in self._SUBTREE_TYPES:
            raise ValueError('This method is only valid on folders.')
        if self.uuid:
            # this is what we do when the entity came from the service
            if not self.__client:
                raise Exception('This method requires a client set')
            self.children = []
            # reset children to avoid duplicating, this way we refresh the cache
            more = True
            page = 1
            while more:
                partial_results = self.__client.list_folder_content(
                    self.uuid, page=page, ordering='name')
                self.children.extend([self.from_dictionary(entity) for entity in partial_results['results']])
                more = partial_results['next'] is not None
                page += 1
        else:
            # there is no uuid, so we explore on disk
            self.children = []
            for child in listdir(self.__disk_path):
                self.children.append(self.from_disk(join(self.__disk_path, child)))
        for child in self.children:
            child.parent = self


    def explore_subtree(self):
        # reset children to avoid duplicating, this way we refresh the cache
        self.children = []
        folders_to_explore = [self]
        while len(folders_to_explore) > 0:
            current_folder = folders_to_explore.pop()
            current_folder.explore_children()
            for entity in current_folder.children:
                if entity.entity_type == 'folder':
                    folders_to_explore.insert(0, entity)

    def load_to_service(self, destination_path=None, destination_uuid=None, subtree=False):
        if not self.__client:
            raise Exception('This method requires a client set')

        if (not (destination_path or destination_uuid) or (destination_path and destination_uuid)):
            raise EntityArgumentException('Exactly one destination is required.')
        if subtree and not self.entity_type in self._SUBTREE_TYPES:
            raise ValueError('This setting is only valid on folders.')
        query = {}
        if destination_path:
            query = {'path': destination_path}
        elif destination_uuid:
            query = {'uuid': destination_uuid}

        parent = self.__client.get_entity_by_query(**query)
        if parent['entity_type'] not in self._SUBTREE_TYPES:
            raise EntityArgumentException('The destination must be a project or folder')

        self.__load(parent['uuid'])
        if subtree:
            self.__process_subtree('__load', None)


    def write_to_disk(self, destination=None, subtree=False):
        '''Write entity to disk

        Args:
            destination: the (existing) folder on disk under which it should be written. If none it will be the home directory
            subtree: to indicate whether we want to write the whole subtree

        '''
        # TODO if subtree then do explore_subtree

        if subtree and not self.entity_type in self._SUBTREE_TYPES:
            raise ValueError('This setting is only valid on folders.')
        destination = destination or os.getcwd()

        self.__write(destination)
        if subtree:
            self.__process_subtree('__write', destination)


    def __process_subtree(self, method, *args):
        '''Iterate subtree and call method(*args) on nodes'''

        if self.entity_type not in self._SUBTREE_TYPES:
            raise ValueError('This setting is only valid on folders.')
        folders_to_process = [self]
        while len(folders_to_process) > 0:
            current_folder = folders_to_process.pop()
            for child in current_folder.children:
                if child.entity_type in self._SUBTREE_TYPES:
                    folders_to_process.insert(0, child)
                getattr(child, method)(*args)

    def __load(self, destination):
        parent_uuid = destination if destination else self.parent.uuid
        if self.entity_type == 'folder':
            self.__load_directory(parent_uuid)
        else:
            self.__load_file(parent_uuid)


    def __load_file(self, parent_uuid):


    def __load_directory(self, parent_uuid):
        parent_uuid = destination if destination else self.parent.uuid
        self.__client.create_folder(name=self.name, parent=parent_uuid)

    def __write(self, destination):
        target_path = '{0}/{1}'.format(destination, self._path)
        if self.entity_type in self._SUBTREE_TYPES:
            self.__create_directory(target_path)
        elif self.entity_type == 'file':
            self.__write_file(target_path)

    def __write_file(self, path):
        # The line below is difficult because we only the entity's path relative
        # to the root of the subtree
        # In order to get the full path we need the full path of the root and
        # concatenating the entity's relative path

        # self.__client.download_file(path=self._path, target_path=path)

        # For now just use the code ..

        signed_url = self.__client.get_signed_url(self.uuid)
        response = self.__client.download_signed_url(signed_url)

        with open(path, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024):
                output.write(chunk)

    @staticmethod
    def __create_directory(path):
        mkdir(path)
