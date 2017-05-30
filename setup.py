'''setup.py'''

# pylint: disable=F0401,E0611

import os

from setuptools import setup, find_packages

import hbp_service_client

import pip
from pip.req import parse_requirements
from optparse import Option


def parse_reqs(reqs_file):
    ''' parse the requirements '''
    options = Option('--workaround')
    options.skip_requirements_regex = None
    # Hack for old pip versions: Versions greater than 1.x
    # have a required parameter "sessions" in parse_requierements
    if pip.__version__.startswith('1.'):
        install_reqs = parse_requirements(reqs_file, options=options)
    else:
        from pip.download import PipSession  # pylint:disable=E0611
        options.isolated_mode = False
        install_reqs = parse_requirements(reqs_file,  # pylint:disable=E1123
                                          options=options,
                                          session=PipSession)
    return [str(ir.req) for ir in install_reqs]

BASEDIR = os.path.dirname(os.path.abspath(__file__))
REQS = parse_reqs(os.path.join(BASEDIR, 'requirements.txt'))

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
