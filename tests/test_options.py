#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import argparse
import os

# Own classes
from nicobot.helpers import *
from nicobot.bot import Bot
from nicobot.bot import ArgsHelper as BotArgsHelper
from nicobot.askbot import Config as AskbotConfig
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


if __name__ == '__main__':
    unittest.main()
