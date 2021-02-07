#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import argparse
import os
import tempfile
import shutil

# Own classes
from nicobot.helpers import *
from nicobot.bot import Bot
from nicobot.bot import ArgsHelper as BotArgsHelper
from nicobot.askbot import Config as AskbotConfig
from nicobot.transbot import Config as TransbotConfig
from nicobot.jabber import arg_parser as jabber_arg_parser
from nicobot.signalcli import ArgsHelper as SignalArgsHelper


class TestOptions(unittest.TestCase):

    def setUp(self):
        self.parser = argparse.ArgumentParser(
            parents=[ BotArgsHelper().parser(), jabber_arg_parser(), SignalArgsHelper().parser() ],
            description='Testing CLI options',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter )

    def test_config_path_default(self):

        # Using AskbotConfig but it could be another one as long as this test is not askbot-specific
        config = AskbotConfig()
        args = []
        config = parse_args_2pass( self.parser, args, config )
        self.assertEqual( 1, len(config.config_dirs) )
        self.assertEqual( os.path.realpath(os.getcwd()), os.path.realpath(config.config_dirs[0]) )

    def test_config_path_custom(self):

        # Using AskbotConfig but it could be another one as long as this test is not askbot-specific
        config = AskbotConfig()
        args = [ '--config-dirs', '/tmp/nicobot' ]
        config = parse_args_2pass( self.parser, args, config )
        self.assertEqual( 1, len(config.config_dirs) )
        self.assertEqual( os.path.realpath('/tmp/nicobot'), os.path.realpath(config.config_dirs[0]) )

    def test_config_path_default_and_custom(self):

        # Using AskbotConfig but it could be another one as long as this test is not askbot-specific
        config = AskbotConfig()
        args = [ '--config-dirs', '/etc/nicobot', '/tmp/nicobot' ]
        config = parse_args_2pass( self.parser, args, config )
        self.assertEqual( 2, len(config.config_dirs) )
        self.assertEqual( os.path.realpath('/etc/nicobot'), os.path.realpath(config.config_dirs[0]) )
        self.assertEqual( os.path.realpath('/tmp/nicobot'), os.path.realpath(config.config_dirs[1]) )

    def test_config_path_with_docker_file_tree(self):
        """
            Tests the default configuration tree of the docker image
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            dir_var_nicobot = os.path.join(tmpdir,'var/nicobot')
            dir_etc_nicobot = os.path.join(tmpdir,'etc/nicobot')
            # 1. Reproduces the initial Docker environment
            shutil.copytree('tests/fixtures/docker_file_tree', tmpdir, dirs_exist_ok=True)
            config = TransbotConfig()
            # Mimics the command line parameters in the docker image
            args = [ '--config-dirs', dir_var_nicobot, dir_etc_nicobot ]
            # 2. Test begins
            config = parse_args_2pass( self.parser, args, config )
            # Directories should be present in the same order
            self.assertEqual( 2, len(config.config_dirs) )
            self.assertEqual( os.path.realpath(dir_var_nicobot), os.path.realpath(config.config_dirs[0]) )
            self.assertEqual( os.path.realpath(dir_etc_nicobot), os.path.realpath(config.config_dirs[1]) )
            # In this fixture there is no '/var/nicobot' directory so /etc/nicobot should be elected
            self.assertEqual( os.path.realpath(os.path.join(dir_etc_nicobot,'config.yml')), os.path.realpath(config.config_file) )
            self.assertEqual( 'console', config.backend )

    def test_config_path_with_docker_var_mount(self):
        """
            Tests a common configuration tree with docker where the user bind-mounts the /var/nicobot directory
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            dir_var_nicobot = os.path.join(tmpdir,'var/nicobot')
            dir_etc_nicobot = os.path.join(tmpdir,'etc/nicobot')
            # 1. Reproduces the initial Docker environment
            shutil.copytree('tests/fixtures/docker_with_var_mount', tmpdir, dirs_exist_ok=True)
            config = TransbotConfig()
            # Mimics the command line parameters in the docker image
            args = [ '--config-dirs', dir_var_nicobot, dir_etc_nicobot ]
            # 2. Test begins
            config = parse_args_2pass( self.parser, args, config )
            # Directories should be present in the same order
            self.assertEqual( 2, len(config.config_dirs) )
            self.assertEqual( os.path.realpath(dir_var_nicobot), os.path.realpath(config.config_dirs[0]) )
            self.assertEqual( os.path.realpath(dir_etc_nicobot), os.path.realpath(config.config_dirs[1]) )
            # In this fixture both '/var/nicobot' and '/etc/nicobot' exist so the first one should be elected
            self.assertEqual( os.path.realpath(os.path.join(dir_var_nicobot,'config.yml')), os.path.realpath(config.config_file) )
            self.assertEqual( 'jabber', config.backend )


if __name__ == '__main__':
    unittest.main()
