'''helper functions for initializing Storage client on the desktop or collab Jupyter notebooks'''

import hbp_service_client.document_service.client import StorageClient

def desktop_get_storage_client(bearer_token):
    return StorageClient(bearer_token)

def collab_get_storage_client():
    return desktop_get_storage_client(oauth.get_token())
