# HBP service client

This library is intended to help Collaboratory Application developers communicate with the core services of the platform in their Python backends or Jupyter notebooks.

## Documentation

For the compiled html documentation visit https://developer.humanbrainproject.eu/docs/hbp-service-client/latest/

## Setup

Install the requirements
```bash
pip install -r requirements.txt \
  -r test/requirements_tests.txt \
  -r doc/requirements_documentation.txt
```

Install the module
```bash
pip install hbp_service_client
```

## Tests
Run the tests
```bash
pytest hbp_service_client
```

## Generating documentation

To compile the HTML documentation execute:

```bash
sphinx-build -d doc/build/doctree doc/source doc/build/html
```
