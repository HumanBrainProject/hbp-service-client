'''setup.py'''

from setuptools import setup, find_packages

import hbp_service_client

with open("requirements.txt") as reqs_file:
    REQS = [line.rstrip() for line in reqs_file.readlines() if line[0] not in ['\n', '-', '#']]

config = {
    'name': 'hbp-service-client',
    'description': ('Python client for the Human Brain Project REST services.'),
    'keywords': 'hbp, human brain project, collaboratory, library, science',
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    'author': 'HBP Infrastructure Developers',
    'author_email': 'platform@humanbrainproject.eu',
    'url': 'https://github.com/HumanBrainProject/hbp-service-client',
    'version': hbp_service_client.__version__,
    'license': 'Apache License 2.0',
    'install_requires': REQS,
    'packages': find_packages(exclude=['doc', '*tests*']),
    'scripts': [],
    'include_package_data': True
    }

setup(**config)
