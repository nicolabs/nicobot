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
from jabber import *
from signalcli import SignalChatter
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
            'recipient': None,
            'signal_cli': shutil.which("signal-cli"),
            'signal_stealth': False,
            'stealth': False,
            'timeout': None,
            'username': None,
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

    parser = argparse.ArgumentParser( description='Sends a XMPP message and reads the answer', formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    # Bootstrap options
    parser.add_argument("--config-file", "-c", "--config", dest="config_file", default=config.config_file, help="YAML configuration file.")
    parser.add_argument("--config-dir", "-C", dest="config_dir", default=config.config_dir, help="Directory where to find configuration files by default.")
    parser.add_argument('--verbosity', '-V', dest='verbosity', default=config.verbosity, help="Log level")
    # Chatter-generic arguments
    parser.add_argument("--backend", "-b", dest="backend", choices=['console','jabber','signal'], default=config.backend, help="Chat backend to use")
    parser.add_argument("--input-file", "-i", dest="input_file", default=config.input_file, help="File to read messages from (one per line)")
    parser.add_argument('--username', '-U', dest='username', help="Sender's ID (a phone number for Signal, a Jabber Identifier (JID) aka. username for Jabber/XMPP")
    parser.add_argument('--recipient', '-r', '--receiver', dest='recipients', default=[], action='append', help="Recipient's ID (e.g. '+12345678901' for Signal / JabberID (Receiver address) to send the message to)")
    parser.add_argument('--stealth', dest='stealth', action="store_true", default=config.stealth, help="Activate stealth mode on any chosen chatter")
    # Other core options
    parser.add_argument('--max-count', dest='max_count', type=int, default=config.max_count, help="Read this maximum number of responses before exiting")
    parser.add_argument('--message', '-m', dest='message', help="Message to send. If missing, will read from --input-file")
    parser.add_argument('--message-file', '-f', dest='message_file', type=argparse.FileType('r'), default=sys.stdin, help="File with the message to send. If missing, will be read from standard input")
    parser.add_argument('--pattern', '-p', dest='patterns', action='append', nargs=2, help="Exits with status 0 whenever a message matches this pattern ; otherwise with status 1")
    parser.add_argument('--timeout', '-t', dest='timeout', type=int, default=config.timeout, help="How much time t wait for an answer before quiting (in seconds)")
    # Misc. options
    parser.add_argument("--debug", "-d", action="store_true", dest='debug', default=False, help="Activate debug logs (overrides --verbosity)")
    # Signal-specific arguments
    parser.add_argument('--signal-cli', dest='signal_cli', default=config.signal_cli, help="Path to `signal-cli` if not in PATH")
    parser.add_argument('--signal-username', dest='signal_username', help="Username when using the Signal backend (overrides --username)")
    parser.add_argument('--signal-group', dest='group', help="Group's ID (for Signal : a base64 string (e.g. 'mPC9JNVoKDGz0YeZMsbL1Q==')")
    parser.add_argument('--signal-recipient', dest='signal_recipients', action='append', default=[], help="Recipient when using the Signal backend (overrides --recipient)")
    parser.add_argument('--signal-stealth', dest='signal_stealth', action="store_true", default=config.signal_stealth, help="Activate Signal chatter's specific stealth mode")
    # Jabber-specific arguments
    parser.add_argument('--jabber-username', '--jabberid', '--jid', dest='jabber_username', help="Username when using the Jabber/XMPP backend (overrides --username)")
    parser.add_argument('--jabber-recipient', dest='jabber_recipients', action='append', default=[], help="Recipient when using the Jabber/XMPP backend (overrides --recipient)")
    parser.add_argument('--jabber-password', dest='jabber_password', help="Senders's password")

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
