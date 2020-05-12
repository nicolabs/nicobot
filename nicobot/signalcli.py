#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os
import shutil
import subprocess
import atexit
import signal
import json
import i18n
import re
import locale

from chatter import Chatter

# Generic timeout for all signal-cli commands
TIMEOUT = 15
# Custom timeout to pass to signal-cli when receiving messages
RECEIVE_TIMEOUT = 5


class SignalChatter(Chatter):
    """
        A signal bot relying on signal-cli
    """

    def __init__( self, username, recipient=None, group=None, signal_cli=shutil.which("signal-cli") ):

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

        # Properties set elsewhere
        self.sentTimestamp = None
        # If True, will terminate the main loop
        self.shutdown = False
        self.bot = None


    def start( self, bot ):

        self.bot = bot

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
        proc = subprocess.run( cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, check=True, timeout=TIMEOUT )
        logging.debug( ">>> %s" % message )

        sent = proc.stdout
        logging.debug("Sent message : %s"%repr(sent))
        self.sentTimestamp = int(sent)


    def reply( self, source ):
        # TODO
        pass


    def stop( self ):

        self.shutdown = True


    def receiveMessages( self, timeout=RECEIVE_TIMEOUT, input=None ):

        cmd = [ self.signal_cli, "-u", self.username, "receive", "--json" ]
        if timeout:
            cmd = cmd + [ "-t", str(timeout) ]

        if not input:
            # TODO Pass this log in finer (lower) level as it can be very verbose and unuseful when reading empty responses every few seconds
            logging.debug(cmd)
            proc = subprocess.Popen( cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE )
            input = proc.stdout
        events = []
        for bline in iter(input.readline, b''):
            logging.debug("Read line : %s" % bline)
            try:
                line = bline.decode()
            except (UnicodeDecodeError, AttributeError):
                line = bline
            events = events + [json.loads(line.rstrip())]

        return events


    def filterMessages( self, events ):

        for event in events:
            logging.debug("Filtering message : %s" % repr(event))
            envelope = event['envelope']
            if envelope['timestamp'] > self.sentTimestamp:
                if envelope['dataMessage']:
                    dataMessage = envelope['dataMessage']
                    if dataMessage['message']:
                        message = event['envelope']['dataMessage']['message']
                        if self.recipient:
                            if envelope['source'] == self.recipient:
                                self.bot.onMessage(message)
                                return True
                            else:
                                logging.debug("Discarding message not from recipient %s"%self.recipient)
                        elif self.group:
                            if dataMessage['groupInfo'] and dataMessage['groupInfo']['groupId']:
                                self.bot.onMessage(message)
                                return True
                            else:
                                logging.debug("Discarding message not from group %s" % self.group)
                    else:
                        logging.debug("Discarding message without text")
                else:
                    logging.debug("Discarding message without data")
            else:
                logging.debug("Discarding message that was sent before ours")

        return False



if __name__ == '__main__':

    """ FIXME This entry point is not working anymore ! """

    parser = argparse.ArgumentParser( description='Sends a XMPP message and reads the answer' )
    # Core parameters
    parser.add_argument('--username', '-u', dest='username', required=True, help="Sender's number (e.g. +12345678901)")
    parser.add_argument('--group', '-g', dest='group', help="Group's ID in base64 (e.g. mPC9JNVoKDGz0YeZMsbL1Q==)")
    parser.add_argument('--recipient', '-r', dest='recipient', help="Recipient's number (e.g. +12345678901)")
    parser.add_argument('--signal-cli', '-s', dest='signal_cli', default=shutil.which("signal-cli"), help="Path to `signal-cli` if not in PATH")
    # Misc. options
    parser.add_argument("--i18n-dir", "-I", dest="i18n_dir", default=os.path.dirname(os.path.realpath(__file__)), help="Directory where to find translation files. Defaults to this script's directory.")
    parser.add_argument('--verbosity', '-V', dest='log_level', default="INFO", help="Log level")
    parser.add_argument("--test", '-T', dest="test", action="store_true", default=False, help="Activate test mode")
    parser.add_argument('--locale', '-L', dest='locale', default=None, help="Change default locale (e.g. 'fr')")
    args = parser.parse_args()

    if not args.signal_cli:
        raise ValueError("Could not find the 'signal-cli' command in PATH and no --signal-cli given")

    if not args.recipient and not args.group:
        raise ValueError("Either --recipient or --group must be provided")

    # Logging configuration
    # TODO Allow for a trace level (high-volume debug)
    # TODO How to tag logs from this module so that their level can be tuned specifically ?
    logLevel = getattr(logging, args.log_level.upper(), None)
    if not isinstance(logLevel, int):
    	raise ValueError('Invalid log level: %s' % args.log_level)
    # Logs are output to stderr ; stdout is reserved to print the answer(s)
    logging.basicConfig(level=logLevel, stream=sys.stderr)

    logging.debug("Current locale : %s"%repr(locale.getlocale()))
    if args.locale:
        loc = args.locale
    else:
        loc = locale.getlocale()[0]

    # See https://pypi.org/project/python-i18n/
    logging.debug("i18n_dir : %s"%args.i18n_dir)
    # FIXME Manually set the locale : how come a Python library named 'i18n' doesn't take into account the Python locale by default ?
    i18n.set('locale',loc.split('_')[0])
    logging.debug("i18n locale : %s"%i18n.get('locale'))
    i18n.set('filename_format', 'i18n.{locale}.{format}')    # Removing the namespace is simpler for us
    i18n.load_path.append(args.i18n_dir)

    # This MUST be instanciated AFTER i18n ha been configured !
    RE_SHUTDOWN = re.compile( i18n.t('Shutdown'), re.IGNORECASE )

    """ Real start """
    bot = SignalChatter( username=args.username, signal_cli=args.signal_cli, recipient=args.recipient, group=args.group )
    if args.test:
        bot.run(sys.stdin)
    else:
        bot.run()
