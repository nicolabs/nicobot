# -*- coding: utf-8 -*-

import atexit
import signal
import sys

class Bot:
    """
        Bot foundation
    """

    def onMessage( self, message ):
        """
            Called by self.chatter whenever a message hsa arrived :
            if the given message contains any of the keywords in any language,
            will answer with a translation in a random language
            including the flag of the random language.

            message: A plain text message
            Returns the crafted translation
        """
        pass


    def onExit( self ):
        """
            Called just before exiting ; the chatter should still be available.
            Subclass MUST call registerExitHandler for this to work !
        """
        pass


    def onSignal( self, sig, frame ):
        # Thanks https://stackoverflow.com/questions/23468042/the-invocation-of-signal-handler-and-atexit-handler-in-python
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
