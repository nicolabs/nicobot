# -*- coding: utf-8 -*-

import argparse
import atexit
import logging
import os
import signal
import sys

from .console import ConsoleChatter
from .jabber import JabberChatter
from .signalcli import SignalChatter
from .stealth import StealthChatter


# There are other options but this one is the most efficient here
# https://github.com/pypa/setuptools_scm#retrieving-package-version-at-runtime
from .version import version as __version__


class Bot:
    """
        Bot foundation
    """

    def onMessage( self, message ):
        """
            Called by self.chatter whenever a message has arrived.

            message: A plain text message
            Returns nothing
        """
        pass


    def onExit( self ):
        """
            Called just before exiting ; the chatter should still be available.
            Subclass MUST call registerExitHandler for this to work !
        """
        logging.debug("Exiting...")


    def onSignal( self, sig, frame ):
        # Thanks https://stackoverflow.com/questions/23468042/the-invocation-of-signal-handler-and-atexit-handler-in-python
        logging.debug("Got signal %s %s",sig,repr(frame))
        sys.exit(0)


    def registerExitHandler( self ):
        # Registers exit handlers to properly say goodbye
        atexit.register(self.onExit)
        # TODO This list does not work on Windows
        for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP ]:
            signal.signal(sig, self.onSignal)

    def run( self ):
        """
            Starts the bot
        """
        pass



class ArgsHelper:

    """
        Command-line parsing helper for bot-generic options
    """

    def __init__(self):

        # Default configuration (some defaults still need to be set up after command line has been parsed)
        self.__dict__.update({
            'backend': "console",
            'config_file': "config.yml",
            'config_dir': os.getcwd(),
            'input_file': sys.stdin,
            'stealth': False,
            'verbosity': "INFO",
            })


    def parser(self):
        """
            Returns a parent parser for common bot arguments
        """

        parser = argparse.ArgumentParser(add_help=False)

        # Bootstrap options
        parser.add_argument("--config-file", "-c", "--config", dest="config_file", default=self.config_file, help="YAML configuration file.")
        parser.add_argument("--config-dir", "-C", dest="config_dir", default=self.config_dir, help="Directory where to find configuration files by default.")
        parser.add_argument('--verbosity', '-v', dest='verbosity', default=self.verbosity, help="Log level")
        # Chatter-generic arguments
        parser.add_argument("--backend", "-b", dest="backend", choices=['console','jabber','signal'], default=self.backend, help="Chat backend to use")
        parser.add_argument("--input-file", "-i", dest="input_file", default=self.input_file, help="File to read messages from (one per line)")
        parser.add_argument('--username', '-U', dest='username', help="Sender's ID (a phone number for Signal, a Jabber Identifier (JID) aka. username for Jabber/XMPP")
        parser.add_argument('--recipient', '-r', '--receiver', dest='recipients', default=[], action='append', help="Recipient's ID (e.g. '+12345678901' for Signal / JabberID (Receiver address) to send the message to)")
        parser.add_argument('--stealth', dest='stealth', action="store_true", default=self.stealth, help="Activate stealth mode on any chosen chatter")
        # Misc. options
        parser.add_argument("--debug", "-d", action="store_true", dest='debug', default=False, help="Activate debug logs (overrides --verbosity)")
        # Needs the .git metadata or some variables to be able to return the version, otherwise throws an error
        # See https://github.com/pypa/setuptools_scm
        parser.add_argument("--version", "-V", action="version", version=__version__)

        return parser


    def jabber_chatter( args ):
        """
            Builds a JabberChatter from Namespace argument 'args'
        """

        username = args.jabber_username if args.jabber_username else args.username
        if not username:
            raise ValueError("Missing --jabber-username")
        if not args.jabber_password:
            raise ValueError("Missing --jabber-password")
        recipients = args.jabber_recipients + args.recipients
        if len(recipients)==0:
            raise ValueError("Missing --jabber-recipient")
        # TODO allow multiple recipients
        return JabberChatter(
            jid=username,
            password=args.jabber_password,
            recipient=recipients[0]
            )


    def signal_chatter( args ):
        """
            Builds a SignalChatter from Namespace argument 'args'
        """

        if not args.signal_cli:
            raise ValueError("Could not find the 'signal-cli' command in PATH and no --signal-cli given")
        username = args.signal_username if args.signal_username else args.username
        if not username:
            raise ValueError("Missing --signal-username")
        recipients = args.signal_recipients + args.recipients
        if len(recipients)==0 and not args.signal_group:
            raise ValueError("Either --signal-recipient or --signal-group must be provided")
        # TODO allow multiple recipients
        return SignalChatter(
            username=username,
            recipient=recipients[0],
            group=args.signal_group,
            signal_cli=args.signal_cli,
            stealth=args.signal_stealth
            )
        # TODO  :timeout=args.timeout


    def chatter( args ):
        """
            Builds the Chatter corresponding to the given parsed command-line arguments
            args: command-line arguments as a Namespace (see argparse)
        """

        if args.backend == 'jabber':
            logging.debug("Jabber/XMPP backend selected")
            chatter = ArgsHelper.jabber_chatter(args)

        elif args.backend == 'signal':
            logging.debug("Signal backend selected")
            chatter = ArgsHelper.signal_chatter(args)

        # By default (or if backend == "console"), will read from stdin or a given file and output to console
        else:
            logging.debug("Console backend selected")
            chatter = ConsoleChatter(args.input_file)

        if args.stealth:
            chatter = StealthChatter(chatter)

        return chatter
