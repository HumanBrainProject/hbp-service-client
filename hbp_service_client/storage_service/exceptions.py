'''local exceptions'''


class StorageException(Exception):
    '''local exception'''
    pass


class StorageArgumentException(StorageException):
    '''Wrong arguments provided'''
    pass


class StorageForbiddenException(StorageException):
    '''403 forbidden'''
    pass


class StorageNotFoundException(StorageException):
    '''404 not found'''
    pass


class EntityException(Exception):
    '''Exception for the Entity class'''
    pass


class EntityDownloadException(Exception):
    '''Error during download'''
    pass


class EntityUploadException(Exception):
    '''Error during upload'''
    pass


class EntityArgumentException(EntityException):
    '''Wrong argument'''
    pass


class EntityInvalidOperationException(EntityException):
    '''Operation cannot be performed on given Entity'''
    pass
