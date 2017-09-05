from os import (mkdir, getcwd)

class Entity(object):

    _SUBTREE_TYPES = ['project', 'folder']
    __client = None

    def __init__(self, entity_type, uuid, name, description):
        self.entity_type = entity_type
        self.uuid = uuid
        self.name = name
        self.description = description
        self.children = []
        self._path = name

    @classmethod
    def set_client(cls, client):
        #verify the interface
        if not hasattr(client, 'storage') and hasattr(client.storage, 'list_folder_content') and callable(client.storage.list_folder_content):
            raise ValueError('The client is of invalid specifications')
        cls.__client = client

    @classmethod
    def from_json(cls, json):
        return cls(
            entity_type=json['entity_type'],
            uuid=json['uuid'],
            name=json['name'],
            description=json['description'])
    @classmethod
    def from_uuid(cls, uuid):
        if not cls.__client:
            raise Exception('This method requires a client set')
        # TODO exception handling
        return cls.from_json(cls.__client.storage.get_entity_details(uuid))

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
        return "({id}: {name}[{type}])".format(id=self.uuid, name=self.name, type=self.entity_type)

    def __repr__(self):
        return self.__str__()

    def explore_children(self):
        if not self.entity_type in self._SUBTREE_TYPES:
            raise ValueError('This method is only valid on folders.')
        if not self.__client:
            raise Exception('This method requires a client set')
        # reset children to avoid duplicating, this way we refresh the cache
        self.children = []
        more = True
        page = 1
        while more:
            partial_results = self.__client.storage.list_folder_content(self.uuid, page=page, ordering='name')
            self.children.extend([self.from_json(entity) for entity in partial_results['results']])
            more = partial_results['next'] is not None
            page += 1
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

    def write_to_disk(self, destination=None, subtree=False):
        '''Write entity to disk

        Args:
            destination: the (existing) folder on disk under which it should be written. If none it will be the home directory
            subtree: to indicate whether we want to write the whole subtree

        '''
        if subtree and not self.entity_type in self._SUBTREE_TYPES:
            raise ValueError('This method is only valid on folders.')
        destination = destination or os.getcwd()

        self.__write(destination)
        if subtree:
            folders_to_write = [self]
            while len(folders_to_write) > 0:
                current_folder = folders_to_write.pop()
                for child in current_folder.children:
                    if child.entity_type in self._SUBTREE_TYPES:
                        folders_to_write.insert(0, child)
                    child.__write(destination)

    def __write(self, destination):
        target_path = '{0}/{1}'.format(destination, self._path)
        if self.entity_type in self._SUBTREE_TYPES:
            self.__create_directory(target_path)
        elif self.entity_type == 'file':
            self.__write_file(target_path)

    def __write_file(self, path):
        with open(path, 'w') as f:
            f.write('foo')

    def __create_directory(self, path):
        os.mkdir(path)
