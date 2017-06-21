'''High-level Client for interacting with the HBP Document Service, providing convenience functions for common operations'''

import hashlib
import json
import logging
import requests
import os

from os.path import join as joinp
from validators import uuid as is_valid_uuid
from hbp_service_client.document_service.client import Client
from hbp_service_client.document_service.requestor import Requestor
from hbp_service_client.document_service.exceptions import (
    DocException, DocArgumentException, DocNotFoundException)


L = logging.getLogger(__name__)

# pylint: disable=W0212

# pylint: disable=W0613
# This is needed for the unused params, which are not used because they are
# gathered via locals()

class StorageClient(Client):
    '''High-level Client for interacting with the HBP Document Service, providing convenience functions for common operations

        Example:
            >>> #you'll have to have an access token ready
            >>> from hbp_service_client.document_service.client import StorageClient
            >>> doc_client = StorageClient.new(my_access_token)
            >>> my_project_contents = doc_client.list_project_content(my_project_id)
    '''

    def __init__(self, requestor, client):
        '''
        Args:
           requestor: the requestor to send the requests with
        '''
        super(StorageClient, self).__init__(requestor)
        self._client = client

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
        requestor = Requestor.new(cls.SERVICE_NAME, cls.SERVICE_VERSION, access_token, environment)
        client = Client.new(access_token, environment)
        return cls(requestor, client)

    def ls(self, path):
        project = self._client.get_entity_by_query(path=path)
        project_uuid = project['uuid']
        file_names = []

        #get files
        more_pages = True
        page_number = 1
        while more_pages:
            response = self._client.list_folder_content(project_uuid, page=page_number)
            more_pages = response['next'] is not None
            page_number += 1
            for child in response['results']:
                pattern = '/{name}' if child['entity_type'] == 'folder' else '{name}'
                file_names.append(pattern.format(name=child['name']))

        return file_names

    def download_file(self, path, target_path):
        entity = self.get_entity_by_query(path=path)
        assert entity['entity_type'] == 'file'

        signed_url = self.get_signed_url(entity['uuid'])
        response = requests.get('https://document/service' + signed_url, stream=True)

        with open(target_path, "wb") as output:
            for chunk in response.iter_content(chunk_size=1024):
                output.write(chunk)

    def exists(self, path):
        try:
            metadata = self.get_entity_by_query(path=path)
            return metadata and 'uuid' in metadata
        except DocNotFoundException:
            return False

    def get_parent(self, path):
        path_steps = path.split('/')
        #extract the last element of the path, which we should be trying to create
        new_dir = path_steps.pop()
        parent_path = "/".join(path_steps)
        return self.get_entity_by_query(path=path)

    def mkdir(self, path):
        parent_metadata = self.get_parent(path)
        self.create_folder(new_dir, parent_metadata['uuid'])
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
            raise DocException('Must specify target file name in dest_path argument')
        if local_file.endswith(os.pathsep):
            raise DocException('Must specify source file name in local_file argument, directory upload not supported')

        path_steps = dest_path.split('/')
        new_file_name = path_steps.pop()
        parent_path = "/".join(path_steps)
        print 'uploading to parent dir:' + parent_path
        parent_metadata = self.get_entity_by_query(path=parent_path)
        #create the file container
        file_details = self.create_file(new_file_name, content_type=mimetype, parent=parent_metadata['uuid'])
        print 'file_details:' + str(file_details)
        etag = self.upload_file_content(file_details['uuid'], source = local_file)

        #NOTE: This should be done inside the upload_file_content itself with a single file read
        if md5check:
            md5_local = self.md5_for_file(local_file, hr=True)
            print 'tags: ' + str(etag) + '?=' + str(md5_local)
            if etag != '"' + md5_local + '"':
                raise DocException('md5 response of server doesn\'t match local file: ' + local_file)
        return (file_details['uuid'],etag)


    def md5_for_file(self, path, block_size=256*128, hr=False):
        '''
        from Stackoverflow: https://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
        Block size directly depends on the block size of your filesystem
        to avoid performances issues
        Here I have blocks of 4096 octets (Default NTFS)
        '''
        md5 = hashlib.md5()
        with open(path,'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                 md5.update(chunk)
        if hr:
            return md5.hexdigest()
        return md5.digest()
