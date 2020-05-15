# -*- coding: utf-8 -*-

import logging
import sys


class ConsoleChatter:
    """
        Bot engine that reads from a stream and outputs to another
    """

    def __init__( self, input=sys.stdin, output=sys.stdout ):
        self.input = input
        self.output = output

    def start( self, bot ):
        for line in self.input:
            bot.onMessage( line )

    def send( self, message ):
        print( message, file=self.output, flush=True )

    def stop( self ):
        sys.exit(0)
