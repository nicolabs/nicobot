# -*- coding: utf-8 -*-

import logging
import sys

from .chatter import Chatter


class StealthChatter(Chatter):
    """
        Wraps a bot engine and prints messages rather than sending them
    """

    def __init__( self, chatter, output=sys.stdout ):
        self.chatter = chatter
        self.output = output

    def start( self, bot ):
        logging.debug("Stealth mode : will not send message")
        self.chatter.start( bot )

    def send( self, message ):
        print( message, file=self.output, flush=True )

    def stop( self ):
        self.chatter.stop()
