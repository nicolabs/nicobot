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
from bot import ArgHelper as BotArgHelper
from console import ConsoleChatter
from jabber import JabberChatter
from jabber import arg_parser as jabber_arg_parser
from signalcli import SignalChatter
from signalcli import ArgHelper as SignalArgHelper
from stealth import StealthChatter


# Default configuration (some defaults still need to be set up after command line has been parsed)
class Config:

    def __init__(self):
        self.__dict__.update({
            'backend': "console",
            'config_file': "config.yml",
            'config_dir': os.getcwd(),
            'input_file': sys.stdin,
            'max_count': -1,
            'patterns': [],
            'stealth': False,
            'timeout': None,
            'verbosity': "INFO",
            })


class Status:

    def __init__(self):
        self.__dict__.update({
            'max_count': False,
            'messages': [],
            })


class AskBot(Bot):
    """
        Sends a message and reads the answer.
        Can be configured with retries, pattern matching, ...

        patterns : a list of 2-element list/tuple as [name,pattern]
    """

    def __init__( self, chatter, message, output=sys.stdout, err=sys.stderr, patterns=[], max_count=-1 ):

        # TODO Implement a global session timeout after which the bot exits
        self.status = Status()
        self.responses_count = 0

        self.chatter = chatter
        self.message = message
        self.output = output
        self.err = err
        self.max_count = max_count
        self.patterns = []
        for pattern in patterns:
            self.patterns.append({ 'name':pattern[0], 'pattern':re.compile(pattern[1]) })


    def onMessage( self, message ):
        """
            Called by self.chatter whenever a message has arrived.

            message: A plain text message
            Returns the full status with exit conditions
        """

        status_message = { 'message':message, 'patterns':[] }
        self.status.messages.append(status_message)

        self.responses_count = self.responses_count + 1
        logging.info("<<< %s", message)

        # If we reached the last message or if we exceeded it (possible if we received several answers in a batch)
        if self.max_count>0 and self.responses_count >= self.max_count:
            logging.debug("Max amount of messages reached")
            self.status.max_count = True

        # Another way to quit : pattern matching
        for p in self.patterns:
            name = p['name']
            pattern = p['pattern']
            status_pattern = { 'name':name, 'pattern':pattern.pattern, 'matched':False }
            status_message['patterns'].append(status_pattern)
            if pattern.search(message):
                logging.debug("Pattern '%s' matched",name)
                status_pattern['matched'] = True
        matched = [ p for p in status_message['patterns'] if p['matched'] ]

        # Check if any exit condition is met to notify the underlying chatter engine
        if self.status.max_count or len(matched) > 0:
            logging.debug("At least one pattern matched : exiting...")
            self.chatter.stop()


    def run( self ):
        """
            Starts the bot :

            1. Sends the given message(s)
            2. Reads and print maximum 'attempts' messages

            Returns the execution status of this bot
        """

        logging.debug("Bot ready.")
        self.registerExitHandler()

        self.chatter.connect()
        # FIXME Sometimes the message is not received by the recipient (but the logs show it's sent ?)
        if self.message:
            self.chatter.send(self.message)

        # Blocks on this line until the bot exits
        logging.debug("Bot reading answer...")
        self.chatter.start(self)

        logging.debug("Bot done.")
        return self.status


if __name__ == '__main__':

    """
        A convenient CLI to play with this bot.

        TODO Put generic arguments in bot.py and inherit from it (should probably provide a parent ArgumentParser)
    """

    #
    # Two-pass arguments parsing
    #

    # config is the final, merged configuration
    config = Config()

    parser = argparse.ArgumentParser(
        parents=[ BotArgHelper().arg_parser(), jabber_arg_parser(), SignalArgHelper().arg_parser() ],
        description='Sends a XMPP message and reads the answer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    # Core options for this bot
    parser.add_argument('--max-count', dest='max_count', type=int, default=config.max_count, help="Read this maximum number of responses before exiting")
    parser.add_argument('--message', '-m', dest='message', help="Message to send. If missing, will read from --input-file")
    parser.add_argument('--message-file', '-f', dest='message_file', type=argparse.FileType('r'), default=sys.stdin, help="File with the message to send. If missing, will be read from standard input")
    parser.add_argument('--pattern', '-p', dest='patterns', action='append', nargs=2, help="Exits with status 0 whenever a message matches this pattern ; otherwise with status 1")
    parser.add_argument('--timeout', '-t', dest='timeout', type=int, default=config.timeout, help="How much time t wait for an answer before quiting (in seconds)")

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
            [args.config_file,
            os.path.join(args.config_dir,"config.yml")],
            should_exist=True,
            fallback_to=1 )[0]
        logging.debug("Using config file %s",config.config_file)
        with open(config.config_file,'r') as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            try:
                # This is the required syntax in newer pyyaml distributions
                dictConfig = yaml.load(file, Loader=yaml.FullLoader)
            except AttributeError:
                # Some systems (e.g. raspbian) ship with an older version of pyyaml
                dictConfig = yaml.load(file)
            logging.debug("Successfully loaded configuration from %s : %s" % (config.config_file,repr(dictConfig)))
            config.__dict__.update(dictConfig)
    except OSError as e:
        # If it was a user-set option, stop here
        if args.config_file == config.config_file:
            raise e
        else:
            logging.debug("Could not open %s ; no config file will be used",config.config_file)
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
    if config.backend == 'jabber':
        logging.debug("Jabber/XMPP backend selected")
        username = config.jabber_username if config.jabber_username else config.username
        if not username:
            raise ValueError("Missing --jabber-username")
        if not config.jabber_password:
            raise ValueError("Missing --jabber-password")
        recipients = config.jabber_recipients + config.recipients
        if len(recipients)==0:
            raise ValueError("Missing --jabber-recipient")
        # TODO allow multiple recipients
        chatter = JabberChatter(
            jid=username,
            password=config.jabber_password,
            recipient=recipients[0]
            )

    elif config.backend == 'signal':
        logging.debug("Signal backend selected")
        if not config.signal_cli:
            raise ValueError("Could not find the 'signal-cli' command in PATH and no --signal-cli given")
        username = config.signal_username if config.signal_username else config.username
        if not username:
            raise ValueError("Missing --signal-username")
        recipients = config.signal_recipients + config.recipients
        if len(recipients)==0 and not config.signal_group:
            raise ValueError("Either --signal-recipient or --signal-group must be provided")
        # TODO allow multiple recipients
        chatter = SignalChatter(
            username=username,
            recipient=recipients[0],
            group=config.signal_group,
            signal_cli=config.signal_cli,
            stealth=config.signal_stealth
            )
        # TODO  :timeout=config.timeout

    # By default (or if backend == "console"), will read from stdin or a given file and output to console
    else:
        logging.debug("Console backend selected")
        chatter = ConsoleChatter(config.input_file,sys.stdout)

    if config.stealth:
        chatter = StealthChatter(chatter)

    #
    # Real start
    #

    bot = AskBot(
        chatter=chatter,
        message=config.message,
        patterns=config.patterns,
        max_count=config.max_count
        )
    status = bot.run()
    print( json.dumps(vars(status)), file=sys.stdout, flush=True )
