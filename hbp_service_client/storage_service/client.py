'''High-level Client for interacting with the HBP Storage Service, providing
convenience functions for common operations'''

import logging
import os

from hbp_service_client.storage_service.api import ApiClient
from hbp_service_client.storage_service.exceptions import (
    StorageArgumentException, StorageNotFoundException)

L = logging.getLogger(__name__)


class Client(object):
    '''A client library for the Storage Service.

        Example:
            >>> #you'll have to have an access token ready
            >>> from hbp_service_client.storage_service.client import Client
            >>> storage_client = Client.new(my_access_token)
            >>> my_project_contents = storage_client.list('/my_project')
    '''

    __BROWSABLE_TYPES = ['project', 'folder']

    def __init__(self, client):
        '''
        Args:
           client: the low level api client
        '''
        self.api_client = client

    @classmethod
    def new(cls, access_token, environment='prod'):
        '''Create new storage service client.

            Arguments:
                environment(str): The service environment to be used for the client.
                    'prod' or 'dev'.
                access_token(str): The access token used to authenticate with the
                    service

            Returns:
                A storage_service.Client instance
        '''

        api_client = ApiClient.new(access_token, environment)
        return cls(api_client)

    def list(self, path):
        '''List the entities found directly under the given path.

        Args:
            path (str): The path of the entity to be listed. Must start with a '/'.

        Returns:
            The list of entity names directly under the given path:

                u'/12345/folder_1'

        Raises:
            StorageArgumentException: Invalid arguments
            StorageForbiddenException: Server response code 403
            StorageNotFoundException: Server response code 404
            StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(path)
        entity = self.api_client.get_entity_by_query(path=path)
        if entity['entity_type'] not in self.__BROWSABLE_TYPES:
            raise StorageArgumentException('The entity type "{0}" cannot be'
                                           'listed'.format(entity['entity_type']))
        entity_uuid = entity['uuid']
        file_names = []

        # get files
        more_pages = True
        page_number = 1
        while more_pages:
            response = self.api_client.list_folder_content(
                entity_uuid, page=page_number, ordering='name')
            more_pages = response['next'] is not None
            page_number += 1
            for child in response['results']:
                pattern = '/{name}' if child['entity_type'] == 'folder' else '{name}'
                file_names.append(pattern.format(name=child['name']))

        return file_names

    def download_file(self, path, target_path):
        '''Download a file from storage service to local disk.

        Existing files on the target path will be overwritten.
        The download is not recursive, as it only works on files.

        Args:
            path (str): The path of the entity to be downloaded. Must start with a '/'.

        Returns:
            None

        Raises:
            StorageArgumentException: Invalid arguments
            StorageForbiddenException: Server response code 403
            StorageNotFoundException: Server response code 404
            StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(path)
        entity = self.api_client.get_entity_by_query(path=path)
        if entity['entity_type'] != 'file':
            raise StorageArgumentException('Only file entities can be downloaded')

        signed_url = self.api_client.get_signed_url(entity['uuid'])
        response = self.api_client.download_signed_url(signed_url)

        with open(target_path, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024):
                output.write(chunk)

    def exists(self, path):
        '''Check if a certain path exists in the storage service.

        Args:
            path (str): The path to be checked

        Returns:
            True if the path exists, False otherwise

        Raises:
            StorageArgumentException: Invalid arguments
            StorageForbiddenException: Server response code 403
            StorageNotFoundException: Server response code 404
            StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(path)
        try:
            metadata = self.api_client.get_entity_by_query(path=path)
        except StorageNotFoundException:
            return False

        return metadata and 'uuid' in metadata

    def get_parent(self, path):
        '''Get the parent entity of the entity pointed by the given path.

        Args:
            path (str): The path of the entity whose parent is needed

        Returns:
            A JSON object of the parent entity if found.

        Raises:
            StorageArgumentException: Invalid arguments
            StorageForbiddenException: Server response code 403
            StorageNotFoundException: Server response code 404
            StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(path, projects_allowed=False)
        path_steps = [step for step in path.split('/') if step]
        del path_steps[-1]
        parent_path = '/{0}'.format('/'.join(path_steps))
        return self.api_client.get_entity_by_query(path=parent_path)

    def mkdir(self, path):
        '''Create a folder in the storage service pointed by the given path.

        Args:
            path (str): The path of the folder to be created

        Returns:
            None

        Raises:
            StorageArgumentException: Invalid arguments
            StorageForbiddenException: Server response code 403
            StorageNotFoundException: Server response code 404
            StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(path, projects_allowed=False)
        parent_metadata = self.get_parent(path)
        self.api_client.create_folder(path.split('/')[-1], parent_metadata['uuid'])
        # no return necessary, function succeeds or we would have thrown an exception
        # before this point.

    def upload_file(self, local_file, dest_path, mimetype):
        '''Upload local file content to a storage service destination folder.

            Args:
                local_file(str)
                dest_path(str):
                    absolute Storage service path '/project' prefix is essential
                    suffix should be the name the file will have on in the destination folder
                    i.e.: /project/folder/.../file_name
                mimetype(str): set the contentType attribute

            Returns:
                The uuid of created file entity as string

            Raises:
                StorageArgumentException: Invalid arguments
                StorageForbiddenException: Server response code 403
                StorageNotFoundException: Server response code 404
                StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(dest_path)
        # get the paths of the target dir and the target file name
        if dest_path.endswith('/'):
            raise StorageArgumentException('Must specify target file name in dest_path argument')
        if local_file.endswith(os.path.sep):
            raise StorageArgumentException('Must specify source file name in local_file'
                                           ' argument, directory upload not supported')

        # create the file container
        new_file = self.api_client.create_file(
            name=dest_path.split('/').pop(),
            content_type=mimetype,
            parent=self.get_parent(dest_path)['uuid']
        )

        etag = self.api_client.upload_file_content(new_file['uuid'], source=local_file)
        new_file['etag'] = etag

        return new_file

    def delete(self, path):
        ''' Delete an entity from the storage service using its path.

            Args:
                path(str): The path of the entity to be delete

            Returns:
                The uuid of created file entity as string

            Raises:
                StorageArgumentException: Invalid arguments
                StorageForbiddenException: Server response code 403
                StorageNotFoundException: Server response code 404
                StorageException: other 400-600 error codes
        '''

        self.__validate_storage_path(path, projects_allowed=False)

        entity = self.api_client.get_entity_by_query(path=path)

        if entity['entity_type'] in self.__BROWSABLE_TYPES:
            # At this point it can only be a folder
            contents = self.api_client.list_folder_content(entity['uuid'])
            if contents['count'] > 0:
                raise StorageArgumentException(
                    'This method cannot delete non-empty folder. Please empty the folder first.')

            self.api_client.delete_folder(entity['uuid'])
        elif entity['entity_type'] == 'file':
            self.api_client.delete_file(entity['uuid'])

    @classmethod
    def __validate_storage_path(cls, path, projects_allowed=True):
        '''Validate a string as a valid storage path'''

        if not path or not isinstance(path, str) or path[0] != '/' or path == '/':
            raise StorageArgumentException(
                'The path must be a string, start with a slash (/), and be longer'
                ' than 1 character.')
        if not projects_allowed and len([elem for elem in path.split('/') if elem]) == 1:
            raise StorageArgumentException(
                'This method does not accept projects in the path.')
