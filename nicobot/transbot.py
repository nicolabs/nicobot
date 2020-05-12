#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Sample bot that translates text whenever it sees a message with one of its keywords.
"""

import argparse
import logging
import sys
import os
import shutil
import json
import i18n
import re
import locale
import requests
import random
# Provides an easy way to get the unicode sequence for country flags
import flag
import yaml

# Own classes
from bot import Bot
from console import ConsoleChatter
from signalcli import SignalChatter


# Default timeout for requests in seconds
# Note : More than 10s recommended (30s ?) on IBM Cloud with a free account
TIMEOUT = 60

# Set to None to translate keywords in all available languages
# Set to something > 0 to limit the number of translations for the keywords (for tests)
LIMIT_KEYWORDS = None

# Default (empty actually) configuration, to ease depth navigation
class Config:

    def __init__(self):
        self.__dict__.update({
            'backend': "console",
            'config_file': None,
            'config_dir': os.getcwd(),
            'group': None,
            'ibmcloud_url': None,
            'ibmcloud_apikey': None,
            'input_file': sys.stdin,
            'keywords': [],
            'keywords_file': None,
            'languages': [],
            'languages_file': None,
            'locale': None,
            'recipient': None,
            'shutdown': None,
            'signal_cli': shutil.which("signal-cli"),
            'username': None,
            'verbosity': "INFO"
            })


"""
    TODO Find a better way to log requests.Response objects
"""
def _logResponse( r ):
    logging.debug("<<< Response : %s\tbody: %.60s[...]", repr(r), r.content )



class TransBot(Bot):
    """
        Sample bot that translates text.

        It only answers to messages containing defined keywords.
        It uses IBM Watson™ Language Translator (see API docs : https://cloud.ibm.com/apidocs/language-translator) to translate the text.
    """


    def __init__( self, chatter, ibmcloud_url, ibmcloud_apikey, keywords=None, keywords_file=None, languages=None, languages_file=None, shutdown_pattern=r'bye nicobot' ):
        """
            keywords: list of keywords that will trigger this bot (in any supported language)
            keywords_file: JSON file where to find the list of keywords (or write into)
            languages: List of supported languages in this format : https://cloud.ibm.com/apidocs/language-translator#list-identifiable-languages
            languages_file: JSON file where to find the list of target languages (or write into)
            shutdown_pattern: a regular expression pattern that terminates this bot
            chatter: the backend chat engine
            ibmcloud_url (required): IBM Cloud API base URL (e.g. 'https://api.eu-de.language-translator.watson.cloud.ibm.com/instances/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx')
            ibmcloud_apikey (required): IBM Cloud API key (e.g. 'dG90byBlc3QgZGFucyBsYSBwbGFjZQo')
            store_path: Base directory where to cache files
        """

        self.ibmcloud_url = ibmcloud_url
        self.ibmcloud_apikey = ibmcloud_apikey
        self.chatter = chatter

        # After IBM credentials have been set we can retrieve the list of supported languages
        if languages:
            self.languages = languages
        else:
            self.languages = self.loadLanguages(file=languages_file)
        # How many different languages to try to translate to
        self.tries = 3

        # After self.languages has been set, we can iterate over to translate keywords
        kws = self.loadKeywords( keywords=keywords, file=keywords_file, limit=LIMIT_KEYWORDS )
        pattern = kws[0]
        for keyword in kws[1:]:
            pattern = pattern + r'|' + keyword
        # Built regular expression pattern that triggers an answer from this bot
        self.re_keywords = pattern
        # Regular expression pattern of messages that stop the bot
        self.re_shutdown = shutdown_pattern


    def loadLanguages( self, force=False, file=None ):
        """
            Loads the list of known languages.

            Requires the IBM Cloud credentials to be set before !

            If force==True then calls the remote service, otherwise reads from the given file if given
        """

        # TODO It starts with the same code as in loadKeywords : make it a function

        # Gets the list from a local file
        if not force and file:
            logging.debug("Reading from %s..." % file)
            try:
                with open(file,'r') as f:
                    j = json.load(f)
                    return j['languages']
            except:
                logging.info("Could not read languages list from %s" % file)
                pass

        # Else, gets the list from the cloud
        # curl --user apikey:{apikey} "{url}/v3/identifiable_languages?version=2018-05-01"
        url = "%s/v3/identifiable_languages?version=2018-05-01" % self.ibmcloud_url
        headers = {
            'Accept': 'application/json',
            'X-Watson-Learning-Opt-Out': 'true'
            }
        logging.debug(">>> GET %s, %s",url,repr(headers))
        r = requests.get(url, headers=headers, auth=('apikey',self.ibmcloud_apikey), timeout=TIMEOUT)
        _logResponse(r)
        if r.status_code == requests.codes.ok:
            # Save it for the next time
            if file:
                try:
                    logging.debug("Saving languages to %s..." % file)
                    with open(file,'w') as f:
                        f.write(r.text)
                except:
                    logging.exception("Could not save the languages list to %s" % file)
                    pass
            else:
                logging.debug("Not saving languages as no file was given")
            return r.json()['languages']
        else:
            r.raise_for_status()


    def loadKeywords( self, keywords=[], file=None, limit=None ):
        """
            Generates a list of translations from a list of keywords.

            Requires self.languages to be filled before !

            If 'keywords' is not empty, will download the translations from IBM Cloud into 'file'.
            Otherwise, will try to read from 'file', falling back to IBM Cloud and saving it into 'file' if it fails.
        """

        # TODO It starts with the same code as in loadLanguages : make it a function

        # Gets the list from a local file
        if not keywords or len(keywords) == 0:
            logging.debug("Reading from %s..." % file)
            try:
                with open(file,'r') as f:
                    j = json.load(f)
                    logging.debug("Read keyword list : %s",repr(j))
                    return j
            except:
                raise ValueError("Could not read keywords list from %s and no keyword given" % file)
                pass

        kws = []

        for keyword in keywords:
            logging.debug("Init %s...",keyword)
            kws = kws + [ keyword ]

            for lang in self.languages:
                # For tests, in order not to use all credits, we can limit the number of calls here
                if limit and len(kws) >= limit:
                    break
                try:
                    translation = self.translate( keyword, target=lang['language'] )
                    translated = translation['translation'].rstrip()
                    logging.debug("Adding translation %s in %s for %s", translated, lang, keyword)
                    kws = kws + [ translated ]
                except:
                    logging.exception("Could not translate %s into %s", keyword, repr(lang))
                    pass
        logging.debug("Keywords : %s", repr(kws))

        if file:
            try:
                logging.debug("Saving keywords translations into %s...", file)
                with open(file,'w') as f:
                    json.dump(kws,f)
            except:
                logging.exception("Could not save keywords translations into %s", file)
                pass
        else:
            logging.debug("Not saving keywords as no file was given")

        return kws


    def translate( self, message, target, source=None ):
        """
            Translates a given message.

            target: Target language short code (e.g. 'en')
            source: Source language short code ; if not given will try to guess

            Returns the plain translated message or None if no translation could be found.
        """

        # curl -X POST -u "apikey:{apikey}" --header "Content-Type: application/json" --data "{\"text\": [\"Hello, world! \", \"How are you?\"], \"model_id\":\"en-es\"}" "{url}/v3/translate?version=2018-05-01"
        url = "%s/v3/translate?version=2018-05-01" % self.ibmcloud_url
        body = {
            "text": [message],
            "target": target
            }
        if source:
            body['source'] = source
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Watson-Learning-Opt-Out': 'true'
            }
        logging.debug(">>> POST %s, %s, %s",url,repr(body),repr(headers))
        r = requests.post(url, json=body, headers=headers, auth=('apikey',self.ibmcloud_apikey), timeout=TIMEOUT)
        # TODO Log full response when it's usefull (i.e. when a message is going to be answered)
        _logResponse(r)
        if r.status_code == requests.codes.ok:
            j = r.json()
            translation = j['translations']
            return translation[0]
        # A 404 can happen if there is no translation available
        elif r.status_code == requests.codes.not_found:
            return None
        else:
            r.raise_for_status()


    def onMessage( self, message ):
        """
            Called by self.chatter whenever a message hsa arrived :
            if the given message contains any of the keywords in any language,
            will answer with a translation in a random language
            including the flag of the random language.

            message: A plain text message
            Returns the crafted translation
        """

        # FIXME re.compile((i18n.t('Shutdown'),re.IGNORECASE).search(message) does not work
        # as expected so we use re.search(...)
        if re.search( self.re_shutdown, message, re.IGNORECASE ):
            logging.debug("Shutdown asked")
            self.chatter.stop()

        # Only if the message contains a keyword
        elif re.search( self.re_keywords, message, flags=re.IGNORECASE ):

            # Selects a few random target languages each time
            langs = random.choices( self.languages, k=self.tries )

            for lang in langs:
                # Gets a translation in this random language
                translation = self.translate( message, target=lang['language'] )
                if translation:
                    translated = translation['translation'].rstrip()
                    try:
                        lang_emoji = flag.flag(lang['language'])
                    except ValueError:
                        lang_emoji= "🏳️‍🌈"
                    answer = "%s %s" % (translated,lang_emoji)
                    logging.debug(">> %s" % answer)
                    self.chatter.send(answer)
                    # Returns as soon as one translation was done
                    return
                else:
                    pass

            logging.warning("Could not find a translation in %s for %s",repr(langs),message)

        else:
            logging.debug("Message did not have a keyword")


    def onExit( self ):

        sent = self.chatter.send( i18n.t('Goodbye') )


    def run( self ):
        """
            Starts the bot :

            1. Sends a hello message
            2. Waits for messages to translate
        """

        self.chatter.send( i18n.t('Hello') )
        self.registerExitHandler()
        self.chatter.start(self)



if __name__ == '__main__':

    """
        A convenient CLI to play with this bot
    """

    #
    # Two-pass arguments parsing
    #

    config = Config()

    parser = argparse.ArgumentParser( description="A bot that reacts to messages with given keywords by responding with a random translation" )
    # Bootstrap options
    parser.add_argument("--config-file", "-c", dest="config_file", help="YAML configuration file.")
    parser.add_argument("--config-dir", "-C", dest="config_dir", default=config.config_dir, help="Directory where to find configuration, cache and translation files by default.")
    parser.add_argument('--verbosity', '-V', dest='verbosity', default=config.verbosity, help="Log level")
    # Core arguments
    parser.add_argument("--keyword", "-k", dest="keywords", action="append", help="Keyword bot should react to (will write them into the file specified with --keywords-file)")
    parser.add_argument("--keywords-file", dest="keywords_file", help="File to load from and write keywords to")
    parser.add_argument("--language", "-l", dest="languages", action="append", help="Target language")
    parser.add_argument("--languages-file", dest="languages_file", help="File to load from and write languages to")
    parser.add_argument("--shutdown", dest="shutdown", help="Shutdown keyword regular expression pattern")
    parser.add_argument("--ibmcloud-url", dest="ibmcloud_url", help="IBM Cloud API base URL (get it from your resource https://cloud.ibm.com/resources)")
    parser.add_argument("--ibmcloud-apikey", dest="ibmcloud_apikey", help="IBM Cloud API key (get it from your resource : https://cloud.ibm.com/resources)")
    # Chatter-generic arguments
    parser.add_argument("--backend", "-b", dest="backend", choices=["signal","console"], default=config.backend, help="Chat backend to use")
    parser.add_argument("--input-file", "-i", dest="input_file", default=config.input_file, help="File to read messages from (one per line)")
    parser.add_argument('--username', '-u', dest='username', help="Sender's number (e.g. +12345678901 for the 'signal' backend)")
    parser.add_argument('--group', '-g', dest='group', help="Group's ID in base64 (e.g. 'mPC9JNVoKDGz0YeZMsbL1Q==' for the 'signal' backend)")
    parser.add_argument('--recipient', '-r', dest='recipient', help="Recipient's number (e.g. +12345678901)")
    # Signal-specific arguments
    parser.add_argument('--signal-cli', dest='signal_cli', default=config.signal_cli, help="Path to `signal-cli` if not in PATH")
    # Misc. options
    parser.add_argument('--locale', '-L', dest='locale', default=config.locale, help="Change default locale (e.g. 'fr')")

    #
    # 1st pass only matters for 'bootstrap' options : configuration file and logging
    #
    parser.parse_args(namespace=config)

    # Logging configuration
    logLevel = getattr(logging, config.verbosity.upper(), None)
    if not isinstance(logLevel, int):
    	raise ValueError('Invalid log level: %s' % config.verbosity)
    # Logs are output to stderr ; stdout is reserved to print the answer(s)
    logging.basicConfig(level=logLevel, stream=sys.stderr)
    logging.debug( "Configuration for bootstrap : %s", repr(vars(config)) )

    # Loads the config file that will be used to lookup some missing parameters
    if not config.config_file:
        config.config_file = os.path.join(config.config_dir,"config.yml")
    try:
        with open(config.config_file,'r') as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            dictConfig = yaml.full_load(file)
            logging.debug("Successfully loaded configuration from %s : %s" % (config.config_file,repr(dictConfig)))
            config.__dict__.update(dictConfig)
    except:
        pass
    # From here the config object has only the default values for all configuration options
    #logging.debug( "Configuration after bootstrap : %s", repr(vars(config)) )

    #
    # 2nd pass parses all options
    #
    # Updates the existing config object with all parsed options
    parser.parse_args(namespace=config)
    logging.debug( "Final configuration : %s", repr(vars(config)) )

    #
    # From here the config object has default options from:
    #   1. hard-coded default values
    #   2. configuration file overrides
    #   3. command line overrides
    #
    # We can check the required options that could not be checked before
    # (because required arguments may have been set from the config file and not on the command line)
    #

    # i18n + l10n
    logging.debug("Current locale : %s"%repr(locale.getlocale()))
    if not config.locale:
        config.locale = locale.getlocale()[0]
    # See https://pypi.org/project/python-i18n/
    # FIXME Manually sets the locale : how come a Python library named 'i18n' doesn't take into account the Python locale by default ?
    i18n.set('locale',config.locale.split('_')[0])
    logging.debug("i18n locale : %s"%i18n.get('locale'))
    i18n.set('filename_format', 'i18n.{locale}.{format}')    # Removing the namespace from keys is simpler for us
    i18n.load_path.append(config.config_dir)

    if not config.ibmcloud_url:
        raise ValueError("Missing required parameter : --ibmcloud-url")
    if not config.ibmcloud_apikey:
        raise ValueError("Missing required parameter : --ibmcloud-apikey")

    # config.keywords is used if given
    # else, check for an existing keywords_file
    if not config.keywords_file:
        # As a last resort, use 'keywords.json' in the config directory
        config.keywords_file = os.path.join(config.config_dir,'keywords.json')
    # Convenience check to better warn the user
    if not config.keywords:
        try:
            with open(config.keywords_file,'r') as f:
                pass
        except:
            raise ValueError("Could not open %s : please generate with --keywords first or create the file indicated with --keywords-file"%config.keywords_file)

    # config.languages is used if given
    # else, check for an existing languages_file
    if not config.languages_file:
        # As a last resort, use 'keywords.json' in the config directory
        config.languages_file = os.path.join(config.config_dir,'languages.json')
    # Convenience check to better warn the user
    if not config.languages:
        try:
            with open(config.languages_file,'r') as f:
                pass
        except:
            raise ValueError("Could not open %s : please remove --languages to generate it automatically or create the file indicated with --languages-file"%config.languages_file)

    if not config.shutdown:
        # This MUST be instanciated AFTER i18n has been configured !
        config.shutdown = i18n.t('Shutdown')

    # Creates the chat engine depending on the 'backend' parameter
    if config.backend == "signal":
        if not config.signal_cli:
            raise ValueError("Could not find the 'signal-cli' command in PATH and no --signal-cli given")
        if not config.username:
            raise ValueError("Missing a username")
        if not config.recipient and not config.group:
            raise ValueError("Either --recipient or --group must be provided")
        chatter = SignalChatter(
            username=config.username,
            recipient=config.recipient,
            group=config.group,
            signal_cli=config.signal_cli)
    # By default (or if backend == "console"), will read from stdin or a given file and output to console
    else:
        chatter = ConsoleChatter(config.input_file,sys.stdout)

    #
    # Real start
    #

    TransBot(
        keywords=config.keywords, keywords_file=config.keywords_file,
        languages=config.languages, languages_file=config.languages_file,
        ibmcloud_url=config.ibmcloud_url, ibmcloud_apikey=config.ibmcloud_apikey,
        shutdown_pattern=config.shutdown,
        chatter=chatter
        ).run()
