#!/usr/bin/env python3
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
from .helpers import *
from .bot import Bot
from .bot import ArgsHelper as BotArgsHelper
from .console import ConsoleChatter
from .jabber import JabberChatter
from .jabber import arg_parser as jabber_arg_parser
from .signalcli import SignalChatter
from .signalcli import ArgsHelper as SignalArgsHelper
from .stealth import StealthChatter


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



class AskBot(Bot):
    """
        Sends a message and reads the answer.
        Can be configured with retries, pattern matching, ...

        patterns : a list of 2-element list/tuple as [name,pattern]
    """

    def __init__( self, chatter, message, patterns=[], max_count=-1 ):

        # TODO Implement a global session timeout after which the bot exits
        self.status = {
            'max_count': False,
            'events': [],
        }
        self.responses_count = 0

        self.chatter = chatter
        self.message = message
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

        status_message = { 'message':message, 'matched_patterns':[] }
        self.status['events'].append(status_message)

        self.responses_count = self.responses_count + 1
        logging.info("<<< %s", message)

        # If we reached the last message or if we exceeded it (possible if we received several answers in a batch)
        if self.max_count>0 and self.responses_count >= self.max_count:
            logging.debug("Max amount of messages reached")
            self.status['max_count'] = True

        # Another way to quit : pattern matching
        matched = status_message['matched_patterns']
        for p in self.patterns:
            name = p['name']
            pattern = p['pattern']
            if pattern.search(message):
                logging.debug("Pattern '%s' matched",name)
                matched.append(name)

        # Check if any exit condition is met to notify the underlying chatter engine
        if self.status['max_count'] or len(matched) > 0:
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



def run( args=sys.argv[1:] ):

    """
        A convenient CLI to play with this bot.

        TODO Put generic arguments in bot.py and inherit from it (should probably provide a parent ArgumentParser)
    """

    # config will be the final, merged configuration
    config = Config()

    parser = argparse.ArgumentParser(
        parents=[ BotArgsHelper().parser(), jabber_arg_parser(), SignalArgsHelper().parser() ],
        description='Sends a XMPP message and reads the answer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    # Core options for this bot
    parser.add_argument('--max-count', dest='max_count', type=int, default=config.max_count, help="Read this maximum number of responses before exiting")
    parser.add_argument('--message', '-m', dest='message', help="Message to send. If missing, will read from --input-file")
    parser.add_argument('--message-file', '-f', dest='message_file', type=argparse.FileType('r'), default=sys.stdin, help="File with the message to send. If missing, will be read from standard input")
    parser.add_argument('--pattern', '-p', dest='patterns', action='append', nargs=2, help="Exits with status 0 whenever a message matches this pattern ; otherwise with status 1")
    parser.add_argument('--timeout', '-t', dest='timeout', type=int, default=config.timeout, help="How much time t wait for an answer before quiting (in seconds)")

    #
    # Two-pass arguments parsing
    #
    config = parse_args_2pass( parser, args, config )
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
    chatter = BotArgsHelper.chatter(config)

    #
    # Real start
    #

    bot = AskBot(
        chatter=chatter,
        message=config.message,
        patterns=config.patterns,
        max_count=config.max_count
        )
    status_args = vars(config)
    # TODO Add an option to list the fields to obfuscate (nor not)
    for k in [ 'jabber_password' ]:
        status_args[k] = '(obfuscated)'
    status_result = bot.run()
    status = { 'args':vars(config), 'result':status_result }
    # NOTE ensure_ascii=False + encode('utf-8').decode() is not mandatory but allows printing plain UTF-8 strings rather than \u... or \x...
    # NOTE default=repr is mandatory because some objects in the args are not serializable
    print( json.dumps(status,skipkeys=True,ensure_ascii=False,default=repr).encode('utf-8').decode(), file=sys.stdout, flush=True )
    # Still returns the full status for simpler handling in Python
    return status


if __name__ == '__main__':

    run()
