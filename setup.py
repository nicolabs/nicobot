#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
#from setuptools_scm import get_version
import re


with open("README.md", "r") as fh:
    long_description = fh.read()


def local_scheme(version):
    return ""

"""
    Very specific Docker tag naming for this project
    This could have been done in Sh, Makefile, ... but here it's integrated
    with the setup script.

    See https://dankeder.com/posts/adding-custom-commands-to-setup-py/
    What variables are available from Githu Actions : https://docs.github.com/en/actions/reference/context-and-expression-syntax-for-github-actions#github-context
"""
class DockerTagsCommand(setuptools.Command):

    description = "Prints a tag list for the given 'base tag'"
    user_options = [
          ('image=', 'i', 'Image name (defaults to nicolabs/nicobot)'),
          ('variant=', 'v', 'Image variant / base tag : debian|debian-signal|alpine'),
          ('branch=', 'b', 'The git ref as <branch name> or refs/heads/<branch name>'),
          ('tag=', 't', 'The git ref as <tag name> or refs/tags/<tag name>'),
          ('ref=', 'r', 'The git ref as refs/tags|heads/<tag or branch name>'),
          ('sep=', 's', 'A string to separate each tag in the output (defaults to a new line)'),
      ]

    def initialize_options(self):
        self.image = 'nicolabs/nicobot'
        self.variant = None
        self.branch = None
        self.tag = None
        self.ref = None
        self.sep = '\n'

    def finalize_options(self):
        """
            ref is the backup value for either tag or branch
            final tag & branch values are normalized anyway
        """

        stag = self.tag
        if not stag and self.ref:
            stag = self.ref
        try:
            # If semver, we don't retain the 'v' prefix
            self.tag = re.search('refs/tags/v?(.*)', stag, flags=re.IGNORECASE).group(1)
        except:
            pass

        sbranch = self.branch
        if not sbranch and self.ref:
            sbranch = self.ref
        try:
            self.branch = re.search('refs/heads/(.*)', sbranch, flags=re.IGNORECASE).group(1)
        except:
            pass

    def run(self):
        # # TODO How to get the actual configuration as set up by setuptools ?
        # version = get_version(local_scheme='no-local-version')
        tags = []
        if self.tag:
            # When git-tagged, the variant name alone means : the 'latest' for this variant
            tags = [ "%s:%s" % (self.image,self.variant) ]
            # It is also tagged with the version
            tags = tags + [ "%s:%s-%s" % (self.image,self.variant,self.tag) ]
            # Only debian-signal is tagged with 'latest' additionaly
            if self.variant == "debian-signal":
                tags = tags + [ "%s:latest" % (self.image) ]
        elif self.branch:
            # All non git-tagged commits overwrite the 'dev' tag (only one is useful currently)
            tags = tags + [ "%s:%s-dev" % (self.image,self.variant) ]
        print( self.sep.join(tags) )


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
    cmdclass = {
        'docker_tags': DockerTagsCommand,
    },
)
