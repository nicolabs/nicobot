#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os
import shutil
import json
import i18n
import re
import locale
import requests
import random
# Provides an easy way to get the unicode sequence for country flags
import flag
import yaml
import urllib.request

# Own classes
from helpers import *
from bot import Bot
from console import ConsoleChatter
from signalcli import SignalChatter
from stealth import StealthChatter


# Default configuration (some defaults still need to be set up after command line has been parsed)
class Config:

    def __init__(self):
        self.__dict__.update({
            'backend': "console",
            'config_file': "config.yml",
            'config_dir': os.getcwd(),
            'group': None,
            'input_file': sys.stdin,
            'recipient': None,
            'signal_cli': shutil.which("signal-cli"),
            'signal_stealth': False,
            'stealth': False,
            'timeout': None,
            'username': None,
            'verbosity': "INFO"
            })



class AskBot(Bot):
    """
        Sends a message and reads the answer.
        Can be configured with retries, pattern matching, ...
    """

    def __init__( self, chatter, input=sys.stdin, output=sys.stdout, err=sys.stderr ):

        self.chatter = chatter
        self.input = input
        self.output = output
        self.err = err


    def onMessage( self, message ):
        """
            Called by self.chatter whenever a message has arrived.

            message: A plain text message
            Returns nothing
        """
        print(message)


    def run( self ):
        """
            Starts the bot :

            1. Sends the given message(s)
            2. Reads and print maximum 'attempts' messages
        """

        logging.debug("Bot starting...")
        self.registerExitHandler()
        for line in self.input:
            self.chatter.send(line)
        self.chatter.start(self)



if __name__ == '__main__':

    """
        A convenient CLI to play with this bot.

        Arguments are compatible with https://github.com/xmpppy/xmpppy/blob/master/xmpp/cli.py and `$HOME/.xtalk`
        but new ones are added.
        TODO Put generic arguments in bot.py and inherit from it (should probably provide a parent ArgumentParser)
    """

    #
    # Two-pass arguments parsing
    #

    # config is the final, merged configuration
    config = Config()

    parser = argparse.ArgumentParser( description='Sends a XMPP message and reads the answer', formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    # Bootstrap options
    parser.add_argument("--config-file", "-c", "--config", dest="config_file", default=config.config_file, help="YAML configuration file.")
    parser.add_argument("--config-dir", "-C", dest="config_dir", default=config.config_dir, help="Directory where to find configuration files by default.")
    parser.add_argument('--verbosity', '-V', dest='verbosity', default=config.verbosity, help="Log level")
    # Chatter-generic arguments
    parser.add_argument("--backend", "-b", dest="backend", choices=["signal","console"], default=config.backend, help="Chat backend to use")
    parser.add_argument("--input-file", "-i", dest="input_file", default=config.input_file, help="File to read messages from (one per line)")
    parser.add_argument('--username', '-u', '--jabberid', dest='username', help="Sender's ID (a phone number for Signal, a Jabber Identifier (JID) aka. username for Jabber/XMPP")
    parser.add_argument('--recipient', '-r', '--receiver', dest='recipient', action='append', help="Recipient's ID (e.g. '+12345678901' for Signal / JabberID (Receiver address) to send the message to)")
    parser.add_argument('--group', '-g', dest='group', help="Group's ID (for Signal : a base64 string (e.g. 'mPC9JNVoKDGz0YeZMsbL1Q==')")
    parser.add_argument('--stealth', dest='stealth', action="store_true", default=config.stealth, help="Activate stealth mode on any chosen chatter")
    # Other core options
    parser.add_argument('--password', '-p', dest='password', help="Senders's password")
    parser.add_argument('--message', '-m', dest='message', help="Message to send. If missing, will read from --input-file")
    parser.add_argument('--message-file', '-f', dest='message_file', type=argparse.FileType('r'), default=sys.stdin, help="File with the message to send. If missing, will be read from standard input")
    parser.add_argument('--timeout', '-t', dest='timeout', type=int, help="How much time t wait for an answer before quiting (in seconds)")
    # Misc. options
    parser.add_argument("--debug", "-d", action="store_true", dest='debug', default=False, help="Activate debug logs (overrides --verbosity)")
    # Signal-specific arguments
    parser.add_argument('--signal-cli', dest='signal_cli', default=config.signal_cli, help="Path to `signal-cli` if not in PATH")
    parser.add_argument('--signal-stealth', dest='signal_stealth', action="store_true", default=config.signal_stealth, help="Activate Signal chatter's specific stealth mode")
    # Jabber-specific arguments
    # TODO

    #
    # 1st pass only matters for 'bootstrap' options : configuration file and logging
    #
    # Note : we don't let the parse_args method merge the 'args' into config yet,
    # because it would not be possible to make the difference between the default values
    # and the ones explictely given by the user
    # This is usefull for instance to throw an exception if a file given by the user doesn't exist, which is different than the default filename
    # 'config' is therefore the defaults overriden by user options while 'args' has only user options
    args = parser.parse_args()

    # Logging configuration
    configure_logging(args.verbosity,debug=args.debug)
    logging.debug( "Configuration for bootstrap : %s", repr(vars(args)) )

    # Fills the config with user-defined default options from a config file
    try:
        # Allows config_file to be relative to the config_dir
        config.config_file = filter_files(
            [config.config_file,
            os.path.join(config.config_dir,"config.yml")],
            should_exist=True,
            fallback_to=1 )[0]
        logging.debug("Using config file %s",config.config_file)
        with open(config.config_file,'r') as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            try:
                # This is the required syntax in newer pyyaml distributions
                dictConfig = yaml.load(file, Loader=yaml.FullLoader)
            except:
                # Some systems (e.g. raspbian) ship with an older version of pyyaml
                dictConfig = yaml.load(file)
            logging.debug("Successfully loaded configuration from %s : %s" % (config.config_file,repr(dictConfig)))
            config.__dict__.update(dictConfig)
    except Exception as e:
        # If it was a user-set option, stop here
        if args.config_file == config.config_file:
            raise e
        else:
            logging.info("Could not read %s ; no config file will be used",config.config_file)
            logging.debug(e, exc_info=True)
            pass
    # From here the config object has only the default values for all configuration options

    #
    # 2nd pass parses all options
    #
    # Updates again the existing config object with all parsed options
    config = parser.parse_args(namespace=config)
    # From the bootstrap parameters, only logging level may need to be read again
    configure_logging(config.verbosity,debug=config.debug)
    logging.debug( "Final configuration : %s", repr(vars(config)) )

    #
    # From here the config object has default options from:
    #   1. hard-coded default values
    #   2. configuration file overrides
    #   3. command line overrides
    #
    # We can now check the required options that could not be checked before
    # (because required arguments may have been set from the config file and not on the command line)
    #

    # Creates the chat engine depending on the 'backend' parameter
    if config.backend == "signal":
        if not config.signal_cli:
            raise ValueError("Could not find the 'signal-cli' command in PATH and no --signal-cli given")
        if not config.username:
            raise ValueError("Missing a username")
        if not config.recipient and not config.group:
            raise ValueError("Either --recipient or --group must be provided")
        chatter = SignalChatter(
            username=config.username,
            recipient=config.recipient[0],
            group=config.group,
            signal_cli=config.signal_cli,
            stealth=config.signal_stealth)
        # TODO  :timeout=config.timeout
    # By default (or if backend == "console"), will read from stdin or a given file and output to console
    else:
        chatter = ConsoleChatter(config.input_file,sys.stdout)

    if config.stealth:
        chatter = StealthChatter(chatter)

    #
    # Real start
    #

    AskBot(
        chatter=chatter
        ).run()
