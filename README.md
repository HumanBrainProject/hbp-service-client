# HBP service client

[![Build Status](https://travis-ci.org/HumanBrainProject/hbp-service-client.svg?branch=master)](https://travis-ci.org/HumanBrainProject/hbp-service-client)

This library is intended to help Collaboratory Application developers communicate with the core services of the platform in their Python backends or Jupyter notebooks.

## Documentation

For the compiled html documentation visit https://developer.humanbrainproject.eu/docs/hbp-service-client/latest/

## Installation

Install the module
```bash
pip install hbp_service_client
```
## Development

### Install the module in editable mode

Install the requirements first

```bash
pip install -r requirements.txt \
  -r test/requirements_tests.txt \
  -r doc/requirements_documentation.txt
```

In the project root directory execute

```bash
pip install -e .
```

### Tests

To run the tests execute the following command from the project root directory.

```bash
pytest
```

### Generating documentation

To compile the HTML documentation execute the following command
after having the module installed in editable mode.

```bash
sphinx-build -d doc/build/doctree doc/source doc/build/html
```

Some RST files in the doc/source directory are not re-generated if they exist already. This might mean that newly added
methods won't get their documentation added to the class's member list. You may have to edit the RST file by hand, or
delete it to have sphinx re-generate it. In the latter case, you might want to rearrange the order of the class members.
