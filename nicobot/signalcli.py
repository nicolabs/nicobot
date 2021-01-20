#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import atexit
import i18n
import json
import locale
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time

from .chatter import Chatter
from .helpers import *


# Generic timeout for signal-cli commands to return (actually only 'send' because 'receive' uses its own timeout)
SEND_TIMEOUT = 30
# Custom timeout to pass to signal-cli when receiving messages (negative values disable timeout)
RECEIVE_TIMEOUT = 5


class SignalChatter(Chatter):
    """
        A signal bot relying on signal-cli
    """

    def __init__( self, username, recipient=None, group=None, signal_cli=shutil.which("signal-cli"), stealth=False, send_timeout=SEND_TIMEOUT, receive_timeout=RECEIVE_TIMEOUT ):

        """
            stealth: if True, will connect and listen to messages but instead of sending answers, will print them
        """

        if not username or not signal_cli:
            raise ValueError("username and signal_cli must be provided")
        if not recipient and not group:
            raise ValueError("Either a recipient or a group must be given")
        if recipient and group:
            raise ValueError("Only one of recipient and group may be given")

        self.username = username
        self.recipient = recipient
        self.group = group
        self.signal_cli = signal_cli
        self.stealth = stealth
        if self.stealth:
            logging.debug("Stealth mode : will not send message")
        self.send_timeout = send_timeout
        self.receive_timeout = receive_timeout

        # Properties set elsewhere
        self.startTime = None
        # If True, will terminate the main loop
        self.shutdown = False
        self.bot = None


    def start( self, bot ):

        self.bot = bot
        # Timestamp in Signal messages is a number of milliseconds since the epoch
        # See https://github.com/signalapp/libsignal-service-java/blob/a88d6a65330ab311079e198dedd25605b1aecc5f/java/src/main/java/org/whispersystems/signalservice/api/messages/SignalServiceDataMessage.java#L344
        self.startTime = time.time() * 1000
        logging.debug("Started at %f",self.startTime)

        while not self.shutdown:
            self.filterMessages( self.receiveMessages() )


    def send( self,  message ):

        cmd = [ self.signal_cli, "-u", self.username, "send", "-m", message ]
        if self.recipient:
            cmd = cmd + [ self.recipient ]
        elif self.group:
            cmd = cmd + [ "-g", self.group ]

        # throws an error in case of status <> 0
        logging.debug(cmd)
        if not self.stealth:
            proc = subprocess.run( cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, check=True, timeout=self.send_timeout )
            sent = proc.stdout
            logging.debug("Sent message : %s"%repr(sent))
        logging.debug( ">>> %s" % message )


    def reply( self, source ):
        # TODO
        pass


    def stop( self ):

        logging.debug("Stopping...")
        self.shutdown = True


    def receiveMessages( self, timeout=None, input=None ):
        """
            timeout: uses self.receive_timeout by default ; negative values disable timeout
        """

        if not timeout:
            timeout = self.receive_timeout

        cmd = [ self.signal_cli, "-u", self.username, "receive", "--json" ]
        if timeout:
            cmd = cmd + [ "-t", str(timeout) ]

        if not input:
            # This log can be very verbose and unuseful when reading empty responses every few seconds
            logging.log(TRACE,cmd)
            proc = subprocess.Popen( cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE )
            input = proc.stdout
        events = []
        for bline in iter(input.readline, b''):
            logging.debug("Read line : %s" % bline)
            # try:
            #     line = bline.decode()
            # except (UnicodeDecodeError, AttributeError):
            #     line = bline
            events = events + [json.loads(bline.rstrip())]

        return events


    def filterMessages( self, events ):

        for event in events:
            logging.debug("Filtering message : %s" % repr(event))
            envelope = event['envelope']
            if envelope['timestamp'] > self.startTime:
                # TODO This test prevents sending and receiving with the same number
                # See https://github.com/nicolabs/nicobot/issues/34
                if envelope['dataMessage']:
                    dataMessage = envelope['dataMessage']
                    if dataMessage['message']:
                        message = event['envelope']['dataMessage']['message']
                        if self.recipient:
                            if envelope['source'] == self.recipient:
                                logging.debug("<<< %s" % message)
                                self.bot.onMessage(message)
                            else:
                                logging.debug("Discarding message not from recipient %s"%self.recipient)
                        elif self.group:
                            if dataMessage['groupInfo'] and dataMessage['groupInfo']['groupId']:
                                logging.debug("<<< %s" % message)
                                self.bot.onMessage(message)
                            else:
                                logging.debug("Discarding message not from group %s" % self.group)
                        else:
                            raise ValueError("Neither a recipient nor a group was configured : we should not be here")
                    else:
                        logging.debug("Discarding message without text")
                else:
                    logging.debug("Discarding message without data")
            else:
                logging.debug("Discarding message that was sent before I started")



class ArgsHelper:

    """
        Command-line parsing helper for Signal-specific options
    """

    def __init__(self):

        # Default configuration (some defaults still need to be set up after command line has been parsed)
        self.__dict__.update({
            'signal_cli': shutil.which("signal-cli"),
            'signal_stealth': False,
            })

    def parser(self):
        """
            Returns a parent parser for Signal-specific arguments
        """

        parser = argparse.ArgumentParser(add_help=False)

        # Signal-specific arguments
        parser.add_argument('--signal-cli', dest='signal_cli', default=self.signal_cli, help="Path to `signal-cli` if not in PATH")
        parser.add_argument('--signal-username', dest='signal_username', help="Username when using the Signal backend (overrides --username)")
        parser.add_argument('--signal-group', dest='signal_group', help="Group's ID (for Signal : a base64 string (e.g. 'mPC9JNVoKDGz0YeZMsbL1Q==')")
        parser.add_argument('--signal-recipient', dest='signal_recipients', action='append', default=[], help="Recipient when using the Signal backend (overrides --recipient)")
        parser.add_argument('--signal-stealth', dest='signal_stealth', action="store_true", default=self.signal_stealth, help="Activate Signal chatter's specific stealth mode")

        return parser
