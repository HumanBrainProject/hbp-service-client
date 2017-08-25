# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/).

## Unreleased

### Added

 * A storage service client `hbp_service_client.storage_service.client` with a higher level abstraction, adding the following methods:
   * TODO when the docstrings are added.

### Changed
 * The module `hbp_service_client.document_service` was renames to `hbp_service_client.storage_service`
 * The module `hbp_service_client.document_service.client` has been replaced by `hbp_service_client.storage_service.client`
 * The old `hbp_service_client.document_service.client.Client` is now available under `hbp_service_client.storage_service.client.Client.api_client`
 * The `Doc(.*)Exception` classes were renamed to `Storage$1Exception`
 * The `hbp_service_client.client.Client.storage` now points to the new `hbp_service_client.storage_service.client`

### Removed

### Fixed
