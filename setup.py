#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

def local_scheme(version):
    return ""

setuptools.setup(
    # See https://packaging.python.org/tutorials/packaging-projects/
    name="nicobot",
    author="nicobo",
    author_email="nicobo@users.noreply.github.com",
    description="A collection of 🤟 cool 🤟 chat bots",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nicolabs/nicobot",
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Topic :: Communications :: Chat',
        'Topic :: Internet :: XMPP',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Software Development :: Internationalization'
    ],
    # PyYAML requires Python 3.5+
    python_requires='>=3.5',
    # TODO This duplicates requirements-build.txt ?
    setup_requires=['setuptools-scm'],
    # TODO This duplicates requirements-runtime.txt
    # Is runnning setup.py enough to replace pip install -r requirements-runtime.txt ?
    install_requires=[
        ##### Requirements for signalcli #####
        'python-i18n',
        ###### Requirements for transbot #####
        'python-i18n',
        # https://requests.readthedocs.io/en/master/
        'requests',
        # https://github.com/cvzi/flag
        'emoji-country-flag',
        # https://pyyaml.org/wiki/PyYAMLDocumentation
        'pyyaml',
        ###### Requirements for jabber #####
        'slixmpp-omemo',
    ],
    entry_points={
        'console_scripts': [
            'askbot=nicobot.askbot:run',
            'transbot=nicobot.transbot:run',
        ],
    },
    # Extracts version from SCM ; https://github.com/pypa/setuptools_scm/
    use_scm_version = {
        "write_to": "nicobot/version.py",
        # Only enable to upload local versions to test repo
        # See https://mixstersite.wordpress.com/2019/12/31/setuptools-with-testpypi-error-invalid-version-pep-440/
        # and https://github.com/pypa/setuptools_scm#user-content-version-number-construction
        "local_scheme": 'no-local-version',
    },
)
