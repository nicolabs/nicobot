# -*- coding: utf-8 -*-

import logging
import sys

from .chatter import Chatter


class ConsoleChatter(Chatter):
    """
        Bot engine that reads messages from a stream (stdin by default)
        and outputs to another stream (stdout by default)
    """

    def __init__( self, input=sys.stdin, output=sys.stdout ):
        self.input = input
        self.output = output
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
        print(message, file = self.output, flush=True)

    def stop( self ):
        self.exit = True
