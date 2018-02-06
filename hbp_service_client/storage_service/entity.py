# pylint: disable=too-many-instance-attributes, too-many-arguments, protected-access
#  - too-many-instance-attributes: An entity has too many attribues, but most of
#      them come from the service
#  - too-many-arguments: Same reason as above
#  - protected-access: we need to access parents' private members. Think of
#      those attributes as private to the class.

'''Abstract tree representation of storage service entities'''

from os import (mkdir, getcwd, walk)
from os.path import (exists, isdir, isfile, isabs, basename, join)
import re
from mimetypes import guess_type, add_type
from validators import uuid as is_valid_uuid
from hbp_service_client.storage_service.api import ApiClient
from hbp_service_client.storage_service.exceptions import (
    EntityArgumentException, EntityInvalidOperationException, EntityException,
    EntityUploadException)


class Entity(object):
    '''A class to represent a storage service entity in a tree.'''
    _SUBTREE_TYPES = ['project', 'folder']
    __client = None

    def __init__(self, entity_type, uuid, name, description, created_by, modified_by,
                 content_type=None):
        self.entity_type = entity_type
        self.__uuid = uuid
        self.name = name
        self.description = description
        self.created_by = created_by
        self.modified_by = modified_by
        self.content_type = content_type
        self.children = []

        self.__parent = None
        self._disk_location = None

    @classmethod
    def set_client(cls, client):
        ''' Set the required API Storage Client for the class.

        Args:
            client (ApiClient): The instantiated API Client
        Raises:
            TypeError: If the specified client is of the wrong type.
        '''

        if not isinstance(client, ApiClient):
            raise TypeError('The client is of invalid specifications')
        cls.__client = client

    @classmethod
    def from_dictionary(cls, dictionary):
        ''' Create an Entity from a dictionary.

        The dictionary must contain the following keys: entity_type, uuid,
            name, description, created_by, modified_by.

        Args:
            dictionary (dict): The dictionary used to construct the entity.

        Returns:
            A properly configured Entity.

        Raises:
            EntityArgumentException: If the supplied argument is of wrong type,
                or has missing keys.
        '''

        try:
            return cls(
                entity_type=dictionary['entity_type'],
                uuid=dictionary['uuid'],
                name=dictionary['name'],
                description=dictionary['description'],
                created_by=dictionary['created_by'],
                modified_by=dictionary['modified_by'],
                content_type=dictionary.get('content_type', None))
        except (TypeError, KeyError) as exc:
            raise EntityArgumentException(exc)

    @classmethod
    def from_uuid(cls, uuid):
        ''' Create an Entity from a uuid.

        The given uuid will be looked up in the storage service, and the results
        are used to create the Entiy object.

        Args:
            uuid (str): The uuid of an entity in the storage service.

        Returns:
            A properly configured Entity.

        Raises:
            EntityException: If a client was not set earlier.
            EntityArgumentException: If the supplied argument is of wrong type.
            StorageNotFoundException: If the uuid could not be looked up.
        '''
        if not cls.__client:
            raise EntityException('This method requires a client set')
        if not is_valid_uuid(uuid):
            raise EntityArgumentException('This method expects a valid UUID.')
        return cls.from_dictionary(cls.__client.get_entity_details(uuid))

    @classmethod
    def from_path(cls, path):
        ''' Create an Entity from a uuid.

        The given path will be looked up in the storage service, and the results
        are used to create the Entiy object.

        Args:
            path (str): The path of an entity in the storage service.

        Returns:
            A properly configured Entity.

        Raises:
            EntityException: If a client was not set earlier.
            StorageNotFoundException: If the path could not be looked up.
        '''
        if not cls.__client:
            raise EntityException('This method requires a client set')
        return cls.from_dictionary(cls.__client.get_entity_by_query(path=path))

    @property
    def uuid(self):
        '''Get the uuid of the Entity'''
        return self.__uuid

    @property
    def parent(self):
        '''Get the parent of the Entity'''

        return self.__parent

    @parent.setter
    def parent(self, parent):
        '''Set the parent of the entity'''

        if not isinstance(parent, type(self)):
            raise ValueError("Parent must be of type {0}".format(type(self)))
        self.__parent = parent

    def __str__(self):
        return "({id}: {name}[{type}])".format(
            id=self.uuid, name=self.name, type=self.entity_type)

    def __repr__(self):
        return self.__str__()

    def explore_children(self):
        '''Find the direct descendents of the Entity in the storage services

        Children entities are constructed from the results and made available in
        the 'children' attribute.

        Returns:
            None

        Raises:
            EntityInvalidOperationException: If the method was called on a file.
            StorageException: An exception occured while talking to the service.
        '''

        if self.entity_type not in self._SUBTREE_TYPES:
            raise EntityInvalidOperationException('This method is only valid on folders.')
        # reset children to avoid duplicating, this way we refresh the cache
        self.children = []

        if not self.__client:
            raise Exception('This method requires a client set')
        more = True
        page = 1
        while more:
            partial_results = self.__client.list_folder_content(
                self.uuid, page=page, ordering='name')
            self.children.extend(
                [self.from_dictionary(entity) for entity in partial_results['results']])
            more = partial_results['next'] is not None
            page += 1
        for child in self.children:
            child.parent = self

    def explore_subtree(self):
        '''Explore descendents from an Entity.

        Children entities are constructed from the results and made available in
        the 'children' attribute. If the Entity is a file it does nothing.

        Returns:
            None

        Raises:
            StorageException: An exception occured while talking to the service.
        '''

        if self.entity_type in self._SUBTREE_TYPES:
            # reset children to avoid duplicating, this way we refresh the cache
            self.children = []
            folders_to_explore = [self]
            while folders_to_explore:
                current_folder = folders_to_explore.pop()
                current_folder.explore_children()
                for entity in current_folder.children:
                    if entity.entity_type == 'folder':
                        folders_to_explore.insert(0, entity)

    def search_subtree(self, regex):
        ''' Search the subtree under the entity in the name field.

        The list of resulting entities will still have their links (parent and
        children) in the tree. The search explores the tree first if it has not
        been explored yet.

        Args:
            regex (str): The regular expression given as a string to use for the search.

        Returns:
            A list of entities with a matching name.

        Raises:
            EntityInvalidOperationException: The search was called on a file Entity.
            EntityArgumentException: The search pattern was not give as a string.
        '''

        if self.entity_type not in self._SUBTREE_TYPES:
            raise EntityInvalidOperationException('You can only seach in folders')
        if not self.children:
            self.explore_subtree()
        if not isinstance(regex, str):
            raise EntityArgumentException('The expression needs to be given as a string')

        results = []
        pattern = re.compile(regex)
        entities_to_check = [self]
        while entities_to_check:
            current_entity = entities_to_check.pop()
            if pattern.search(current_entity.name):
                results.append(current_entity)
            for entity in current_entity.children:
                entities_to_check.insert(0, entity)
        return results

    def upload(self, path):
        '''Upload an entity into the storage service.

        The parent can be identified either via path or uuid.

        Args:
            destination_path: The path of the parent folder/project in the service
            destination_uuid: The uuid of the parent folder/project in the service

        Raises:
            EntityArgumentException: Too many or little arguments were provided.
            StorageNotFoundException: The parent entity could not be found.
        '''
        if not self.__client:
            raise EntityException('This method requires a client set')

        if self.entity_type not in self._SUBTREE_TYPES:
            raise EntityInvalidOperationException('Files cannot be destinations')

        if not isabs(path):
            raise EntityArgumentException('The path must be given as an absolute path')

        if path[-1] == '/':
            path = path[:-1]

        if not exists(path):
            raise EntityArgumentException('The given path does not exist on the disk.')

        if self.__client.list_folder_content(self.uuid, name=basename(path))['count'] != 0:
            raise EntityUploadException('An entity with the same name and '
                                        'type already exists at the destination')

        if self.entity_type in self._SUBTREE_TYPES and not self.children:
            self.explore_subtree()

        self.__load(path)

    def download(self, destination=None):
        '''Download an entity recursively from the service to local disk.

        The download explores the tree first if it has not been explored yet.
        Args:
            destination (str): An existing folder on disk in which the entity
                should be downloaded. If not given the current working
                directory will be used.
        Raises:
            OSError: If a file/folder with the entity's name already exists
                on disk, or the destination directory is missing.
        '''

        if not self.__client:
            raise EntityException('This method requires a client set')

        if self.entity_type in self._SUBTREE_TYPES and not self.children:
            self.explore_subtree()
        destination = destination or getcwd()

        self.__process_subtree('__write', destination=destination, relative_root=self)

    def __process_subtree(self, method, *args, **kwargs):
        '''Iterate subtree and call private method(**args)(**kwargs) on nodes'''

        entities_to_process = [self]
        while entities_to_process:
            current_entity = entities_to_process.pop()
            for child in current_entity.children:
                entities_to_process.insert(0, child)
            getattr(
                current_entity,
                '_{classname}{methodname}'.format(
                    classname=self.__class__.__name__,
                    methodname=method))(*args, **kwargs)

    def __load(self, path):
        '''Load fs object at path to the storage service under self'''
        if isfile(path):
            self.children.append(self.__load_file(self.uuid, path))
        elif isdir(path):
            newdir = self.__load_directory(self.uuid, path)
            self.children.append(newdir)
            created_folder_entities = {path: newdir}
            for root, folders, files in walk(path):
                parent = created_folder_entities[root]
                for currentfile in files:
                    newfile = self.__load_file(parent.uuid, join(root, currentfile))
                    parent.children.append(newfile)
                for currentfolder in folders:
                    newdir = self.__load_directory(parent.uuid, join(root, currentfolder))
                    created_folder_entities[join(root, currentfolder)] = newdir
                    parent.children.append((newdir))
        else:
            raise EntityArgumentException('Only regular files and directories are supported.')

    @classmethod
    def __load_file(cls, parent_uuid, path):
        '''Load a single file into the storage service. Return the description.'''
        add_type('application/x-ipynb+json', '.ipynb')
        new_file = cls.__client.create_file(
            name=basename(path),
            parent=parent_uuid,
            content_type=guess_type(basename(path))[0] or 'application/octet-stream')
        cls.__client.upload_file_content(
            file_id=new_file['uuid'],
            source=path)
        return Entity.from_dictionary(new_file)

    @classmethod
    def __load_directory(cls, parent_uuid, path):
        '''Load a single directory into the storage service. Return the description.'''
        return Entity.from_dictionary(
            cls.__client.create_folder(name=basename(path), parent=parent_uuid))

    def __write(self, destination, relative_root):
        '''Write entities to disk

        Their position in the tree will be determined by the relative_root.
        The write operation assumes that the directory structure up to the
        relative_root has been created already.
        '''

        self._disk_location = join(
            destination if self == relative_root else self.parent._disk_location,
            self.name)

        if self.entity_type in self._SUBTREE_TYPES:
            self.__create_directory()
        elif self.entity_type == 'file':
            self.__write_file()

    def __write_file(self):
        '''Write a single file to disc'''
        if isfile(self._disk_location):
            raise OSError('The target file already exists')

        signed_url = self.__client.get_signed_url(self.uuid)
        response = self.__client.download_signed_url(signed_url)

        with open(self._disk_location, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024):
                output.write(chunk)

    def __create_directory(self):
        '''Write a single directory to the disk'''
        mkdir(self._disk_location)
