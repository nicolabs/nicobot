# -*- coding: utf-8 -*-

import logging
import sys

from .chatter import Chatter


class ConsoleChatter(Chatter):
    """
        Bot engine that reads messages from a stream (stdin by default)
    """

    def __init__( self, input=sys.stdin ):
        self.input = input
        self.exit = False

    def start( self, bot ):
        # TODO Do it asynchronous (rather than testing self.exit between each instruction)
        if self.exit:
            return
        for line in self.input:
            if self.exit:
                return
            logging.debug( "<<< %s", line )
            bot.onMessage( line.rstrip() )
            if self.exit:
                return

    def send( self, message ):
        logging.debug( ">>> %s", message )

    def stop( self ):
        self.exit = True
