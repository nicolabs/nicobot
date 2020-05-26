# -*- coding: utf-8 -*-

import argparse
import asyncio
import logging
import os
import time

from slixmpp import ClientXMPP, JID
from slixmpp.exceptions import IqTimeout, IqError
from slixmpp.stanza import Message
import slixmpp_omemo
from slixmpp_omemo import PluginCouldNotLoad, MissingOwnKey, EncryptionPrepareException
from slixmpp_omemo import UndecidedException, UntrustedException, NoAvailableSession
from omemo.exceptions import MissingBundleException

# Own classes
from .chatter import Chatter
from .helpers import *



class SliXmppClient(ClientXMPP):

    """
        This generic XMPP client is able to send & receive plain & OMEMO-encrypted messages.

        Code is mostly taken from https://lab.louiz.org/poezio/slixmpp-omemo/-/blob/master/examples/echo_client.py
    """

    eme_ns = 'eu.siacs.conversations.axolotl'

    def __init__(self, jid, password, message_handler):

        """
            jid, password : valid account to send and receive messages
            message_handler : a Callable( original_message:Message, decrypted_body )
        """

        ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # XMPP Ping
        self.register_plugin('xep_0380') # Explicit Message Encryption

        try:
            self.register_plugin(
                'xep_0384',
                {
                    'data_dir': '.omemo',
                },
                module=slixmpp_omemo,
            ) # OMEMO
        except (PluginCouldNotLoad,):
            log.exception('And error occured when loading the omemo plugin.')
            sys.exit(1)

        self.message_handler = message_handler


    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        # Most get_*/set_* methods from plugins use Iq stanzas, which
        # can generate IqError and IqTimeout exceptions
        #
        # try:
        #     self.get_roster()
        # except IqError as err:
        #     logging.error('There was an error getting the roster')
        #     logging.error(err.iq['error']['condition'])
        #     self.disconnect()
        # except IqTimeout:
        #     logging.error('Server is taking too long to respond')
        #     self.disconnect()


    async def message(self, msg: Message, allow_untrusted: bool = False) -> None:
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """

        # Sample encrypted message :
        #
        # <message xml:lang="en" to="bot9cd51f1a@conversations.im/1655465886336291765177990819" from="bot649ad4ad@conversations.im/Conversations.7Z6J" type="chat" id="26a30844-37d0-4f27-8daa-fd2107f5e706"><archived xmlns="urn:xmpp:mam:tmp" by="bot9cd51f1a@conversations.im" id="1590067423912722"/><stanza-id xmlns="urn:xmpp:sid:0" by="bot9cd51f1a@conversations.im" id="1590067423912722"/>
        #     <encrypted xmlns="eu.siacs.conversations.axolotl">
        #         <header sid="307701646">
        #             <key rid="45781751">MwohBadGcbUIiKsYACIw8UjlZHsOEf79+fjBM44O9bM1YatXKRKaIYuaIkajsedDkIK906Srxk2N5B7jh8EozEAFKpfeqZg//Hqrin6wOGpX+TZ5kUJziXIALUaRs59D3J0=</key>
        #             <key rid="1929813965">MwohBWTCE+eWLNmdgTy/gyEAAYACIwzz9+B/UFiaCu+5rcHmh3tyQ/GgBhVa+mk81YkQErXpjCpAPyWbKVJn2TH1dXH4Yj7VYYis0HDQ7r28ZDcMMXoxFcp2VNO9l7S23wI=</key>
        #             <iv>5eM9IHpWSbKfLJj6</iv>
        #         </header>
        #         <payload>pX7D+54c</payload>
        #     </encrypted><request xmlns="urn:xmpp:receipts"/><markable xmlns="urn:xmpp:chat-markers:0"/><origin-id xmlns="urn:xmpp:sid:0" id="26a30844-37d0-4f27-8daa-fd2107f5e706"/><store xmlns="urn:xmpp:hints"/><encryption xmlns="urn:xmpp:eme:0" name="OMEMO" namespace="eu.siacs.conversations.axolotl"/>
        #     <body>I sent you an OMEMO encrypted message but your client doesn’t seem to support that. Find more information on https://conversations.im/omemo</body>
        # </message>

        # Sample plain message :
        # <message xml:lang="en" to="bot9cd51f1a@conversations.im/11834511835037473566179797763" from="bot649ad4ad@conversations.im/Conversations.7Z6J" type="chat" id="5677cbdf-11d2-4aed-889e-0fb3e850a390"><archived xmlns="urn:xmpp:mam:tmp" by="bot9cd51f1a@conversations.im" id="1590095998371956"/><stanza-id xmlns="urn:xmpp:sid:0" by="bot9cd51f1a@conversations.im" id="1590095998371956"/><request xmlns="urn:xmpp:receipts"/><markable xmlns="urn:xmpp:chat-markers:0"/><origin-id xmlns="urn:xmpp:sid:0" id="5677cbdf-11d2-4aed-889e-0fb3e850a390"/><active xmlns="http://jabber.org/protocol/chatstates"/>
        #     <body>My message</body>
        # </message>

        logging.debug("XMPP message received : %r",msg)

        # TODO ? with xmppy I used to allow the following types : ["message","chat","normal",None]
        if msg['type'] not in ('chat', 'normal'):
            logging.debug("Discarding message of type %r",msg['type'])
            return None

        if not self['xep_0384'].is_encrypted(msg):
            logging.debug('This message was not encrypted')
            self.message_handler(msg,msg['body'])
            return None

        try:
            mfrom = msg['from']
            encrypted = msg['omemo_encrypted']
            body = self['xep_0384'].decrypt_message(encrypted, mfrom, allow_untrusted)
            # TODO Is it always UTF-8-encoded ?
            self.message_handler(msg,body.decode("utf8"))
            return None
        except (MissingOwnKey,):
            # The message is missing our own key, it was not encrypted for
            # us, and we can't decrypt it.
            logging.exception('I can\'t decrypt this message as it is not encrypted for me : %r',msg)
            return None
        except (NoAvailableSession,):
            # We received a message from that contained a session that we
            # don't know about (deleted session storage, etc.). We can't
            # decrypt the message, and it's going to be lost.
            # Here, as we need to initiate a new encrypted session, it is
            # best if we send an encrypted message directly. XXX: Is it
            # where we talk about self-healing messages?
            logging.exception('I can\'t decrypt this message as it uses an encrypted session I don\'t know about : %r',msg)
            return None
        except (UndecidedException, UntrustedException) as exn:
            # We received a message from an untrusted device. We can
            # choose to decrypt the message nonetheless, with the
            # `allow_untrusted` flag on the `decrypt_message` call, which
            # we will do here. This is only possible for decryption,
            # encryption will require us to decide if we trust the device
            # or not. Clients _should_ indicate that the message was not
            # trusted, or in undecided state, if they decide to decrypt it
            # anyway.
            logging.exception("Your device '%s' is not in my trusted devices.", exn.device)
            # We resend, setting the `allow_untrusted` parameter to True.
            await self.message(msg, allow_untrusted=True)
            return None
        except (EncryptionPrepareException,):
            # Slixmpp tried its best, but there were errors it couldn't
            # resolve. At this point you should have seen other exceptions
            # and given a chance to resolve them already.
            logging.exception('I was not able to decrypt the message : %r',msg)
            return None
        except (Exception,):
            logging.exception('An error occured while attempting decryption')
            raise

        return None


    async def plain_send(self, body, receiver, type='chat'):
        """
        Helper to send messages
        """

        msg = self.make_message(mto=receiver, mtype=type)
        msg['body'] = body
        return msg.send()


    async def plain_reply(self, original_msg, body):
        """
        Helper to reply to messages
        """

        return self.plain_send( body, original_msg['from'], original_msg['type'] )


    async def encrypted_send(self, body, recipient, type='chat'):
        """Helper to send encrypted messages"""

        msg = self.make_message(mto=recipient, mtype=type)
        msg['eme']['namespace'] = self.eme_ns
        msg['eme']['name'] = self['xep_0380'].mechanisms[self.eme_ns]

        expect_problems = {}  # type: Optional[Dict[JID, List[int]]]

        while True:
            try:
                # `encrypt_message` excepts the plaintext to be sent, a list of
                # bare JIDs to encrypt to, and optionally a dict of problems to
                # expect per bare JID.
                #
                # Note that this function returns an `<encrypted/>` object,
                # and not a full Message stanza. This combined with the
                # `recipients` parameter that requires for a list of JIDs,
                # allows you to encrypt for 1:1 as well as groupchats (MUC).
                #
                # `expect_problems`: See EncryptionPrepareException handling.
                recipients = [JID(recipient)]
                encrypt = await self['xep_0384'].encrypt_message(body, recipients, expect_problems)
                msg.append(encrypt)
                return msg.send()
            except UndecidedException as exn:
                # The library prevents us from sending a message to an
                # untrusted/undecided barejid, so we need to make a decision here.
                # This is where you prompt your user to ask what to do. In
                # this bot we will automatically trust undecided recipients.
                self['xep_0384'].trust(exn.bare_jid, exn.device, exn.ik)
            # TODO: catch NoEligibleDevicesException
            except EncryptionPrepareException as exn:
                # This exception is being raised when the library has tried
                # all it could and doesn't know what to do anymore. It
                # contains a list of exceptions that the user must resolve, or
                # explicitely ignore via `expect_problems`.
                # TODO: We might need to bail out here if errors are the same?
                for error in exn.errors:
                    if isinstance(error, MissingBundleException):
                        # We choose to ignore MissingBundleException. It seems
                        # to be somewhat accepted that it's better not to
                        # encrypt for a device if it has problems and encrypt
                        # for the rest, rather than error out. The "faulty"
                        # device won't be able to decrypt and should display a
                        # generic message. The receiving end-user at this
                        # point can bring up the issue if it happens.
                        logging.warning('Could not find keys for device "%d" of recipient "%s". Skipping.', error.device, error.bare_jid)
                        jid = JID(error.bare_jid)
                        device_list = expect_problems.setdefault(jid, [])
                        device_list.append(error.device)
            except (IqError, IqTimeout) as exn:
                logging.exception('An error occured while fetching information on %r', recipient)
                return None
            except Exception as exn:
                logging.exception('An error occured while attempting to encrypt to %r', recipient)
                raise

        return None


    async def encrypted_reply(self, original_msg, body):
        """Helper to reply with encrypted messages"""

        logging.debug("Replying to %r",original_msg)
        return self.encrypted_send( body, recipient=original_msg['from'], type=original_msg['type'] )



class JabberChatter(Chatter):

    """
        Sends and receives messages with XMPP (a.k.a. Jabber).

        It implements nicobot.Chatter by wrapping an internal slixmpp.ClientXMPP instance.
    """

    def __init__( self, jid, password, recipient ):

        self.recipient = recipient
        self.xmpp = SliXmppClient( jid, password, message_handler=self.on_xmpp_message )

    def on_xmpp_message( self, original_message, decrypted_body ):
        """
            Called by the internal xmpp client when a message has arrived.

            original_message: The received Message instance
            decrypted_body: either the given body if it was plain text or the OMEMO-decrypted one (always a string)
        """

        logging.log(TRACE,"<<< %r",original_message)
        logging.debug("<<< %r",decrypted_body)
        self.bot.onMessage(decrypted_body)

    def connect(self):

        logging.debug("Connecting...")
        # Connects and waits for the connection to be established
        # See https://slixmpp.readthedocs.io/using_asyncio.html
        self.xmpp.connected_event = asyncio.Event()
        callback = lambda _: self.xmpp.connected_event.set()
        self.xmpp.add_event_handler('session_start', callback)
        self.xmpp.connect()
        # TODO use asyncio.run() in latest python
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.xmpp.connected_event.wait())
        logging.debug("Connected.")

    def start( self, bot ):
        """
            Waits for messages and calls the 'onMessage' method of the given Bot
        """
        self.bot = bot
        # do some other stuff before running the event loop, e.g.
        # loop.run_until_complete(httpserver.init())
        self.xmpp.process(forever=False)
        # FIXME Following error when exiting :
        # Task was destroyed but it is pending! task: <Task pending coro=<XMLStream.run_filters() running at /home/./.local/lib/python3.6/site-packages/slixmpp/xmlstream/xmlstream.py:972> wait_for=<Future pending cb=[<TaskWakeupMethWrapper object at 0x7fa91adc0fd8>()]>>

    def send( self, message ):
        """
            Sends the given message using the underlying implemented chat protocol
        """
        logging.debug(">>> %s",message)
        # TODO use asyncio.make_task() in latest python
        asyncio.ensure_future( self.xmpp.encrypted_send( body=message, recipient=self.recipient ) )

    def stop( self ):
        """
            Stops waiting for messages and exits the engine
        """
        self.xmpp.disconnect()



def arg_parser():
    """
        Returns a parent parser for jabber-specific arguments
    """

    parser = argparse.ArgumentParser(add_help=False)

    # Jabber-specific arguments
    parser.add_argument('--jabber-username', '--jabberid', '--jid', dest='jabber_username', help="Username when using the Jabber/XMPP backend (overrides --username)")
    parser.add_argument('--jabber-recipient', dest='jabber_recipients', action='append', default=[], help="Recipient when using the Jabber/XMPP backend (overrides --recipient)")
    parser.add_argument('--jabber-password', dest='jabber_password', help="Senders's password")

    return parser
