# -*- coding: utf-8 -*-


class Chatter:
    """
        Bot engine interface
    """

    def connect(self):
        """
            Connects / initializes the connection with the underlying protocol/network if required.
            This should always be called before any other method in order to make sure the bot is connected.
        """
        pass

    def start( self, bot ):
        """
            Waits for messages and calls the 'onMessage' method of the given Bot
        """
        pass

    def reply( self, source ):
        """
            Replies to a specific message or person
        """
        pass

    def send( self, message ):
        """
            Sends the given message using the underlying implemented chat protocol
        """
        pass

    def stop( self ):
        """
            Stops waiting for messages and exits the engine
        """
        pass
