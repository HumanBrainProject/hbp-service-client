'''High-level Client for interacting with the HBP Storageument Service, providing convenience functions for common operations'''

import hashlib
import json
import logging
import requests
import os

from os.path import join as joinp
from validators import uuid as is_valid_uuid
from hbp_service_client.storage_service.api import ApiClient
from hbp_service_client.storage_service.exceptions import (
    StorageException, StorageArgumentException, StorageNotFoundException)


L = logging.getLogger(__name__)

# pylint: disable=W0212

# pylint: disable=W0613
# This is needed for the unused params, which are not used because they are
# gathered via locals()

class Client(object):
    '''High-level Client for interacting with the HBP Document Service, providing convenience functions for common operations

        Example:
            >>> #you'll have to have an access token ready
            >>> from hbp_service_client.storage_service.client import Client
            >>> doc_client = Client.new(my_access_token)
            >>> my_project_contents = doc_client.list_project_content(my_project_id)
    '''

    def __init__(self, client):
        '''
        Args:
           client: the low level api client
        '''
        self.api_client = client

    @classmethod
    def new(cls, access_token, environment='prod'):
        '''Create new documentservice client

            Arguments:
                environment: The service environment to be used for the client
                access_token: The access token used to authenticate with the
                    service

            Returns:
                A document_service.Client instance

        '''
        apiClient = ApiClient.new(access_token, environment)
        return cls(apiClient)

    def ls(self, path):
        project = self.api_client.get_entity_by_query(path=path)
        project_uuid = project['uuid']
        file_names = []

        #get files
        more_pages = True
        page_number = 1
        while more_pages:
            response = self.api_client.list_folder_content(project_uuid, page=page_number)
            more_pages = response['next'] is not None
            page_number += 1
            for child in response['results']:
                pattern = '/{name}' if child['entity_type'] == 'folder' else '{name}'
                file_names.append(pattern.format(name=child['name']))

        return file_names

    def download_file(self, path, target_path):
        entity = self.api_client.get_entity_by_query(path=path)
        assert entity['entity_type'] == 'file'

        signed_url = self.api_client.get_signed_url(entity['uuid'])
        response = self.api_client.download_signed_url(signed_url)

        with open(target_path, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024):
                output.write(chunk)

    def exists(self, path):
        try:
            metadata = self.api_client.get_entity_by_query(path=path)
        except StorageNotFoundException:
            return False

        return metadata and 'uuid' in metadata

    def get_parent(self, path):
        path_steps = path.split('/')
        new_dir = path_steps.pop()
        parent_path = "/".join(path_steps)
        return self.api_client.get_entity_by_query(path=parent_path)

    def mkdir(self, path):
        parent_metadata = self.get_parent(path)
        self.api_client.create_folder(path.split('/').pop(), parent_metadata['uuid'])
        #no return necessary, function succeeds or we would have thrown an exception before this point.

    def upload_file(self,local_file, dest_path, mimetype, md5check=False):
        '''upload local file content to a Storage service destination folder

            Args:
                local_file(string path)
                dest_path(string path):
                    absolute Storage service path '/project' prefix is essential
                    suffix should be the name the file will have on in the destination folder
                    i.e.: /project/folder/.../file_name
                mimetype(str): set the contentType attribute
                storage_attributes(dict): override standard storage metadata attributes

            Returns: uuid of created file entity
        '''
        #get the paths of the target dir and the target file name
        if dest_path.endswith('/'):
            raise StorageArgumentException('Must specify target file name in dest_path argument')
        if local_file.endswith(os.path.sep):
            raise StorageArgumentException('Must specify source file name in local_file argument, directory upload not supported')

        #create the file container
        new_file = self.api_client.create_file(
            name         = dest_path.split('/').pop(),
            content_type = mimetype,
            parent       = self.get_parent(dest_path)['uuid']
        )

        etag = self.api_client.upload_file_content(new_file['uuid'], source = local_file)
        new_file['etag'] = etag

        return new_file
