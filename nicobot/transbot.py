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
from helpers import *
from bot import Bot
from console import ConsoleChatter
from signalcli import SignalChatter
from stealth import StealthChatter



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
            'keywords_files': [],
            'languages': [],
            'languages_file': None,
            # e.g. locale.getlocale() may return ('en_US','UTF-8') : we only keep the 'en_US' part here (the same as the expected command-line parameter)
            'locale': locale.getlocale()[0],
            'recipient': None,
            'shutdown': None,
            'signal_cli': shutil.which("signal-cli"),
            'signal_stealth': False,
            'stealth': False,
            'username': None,
            'verbosity': "INFO"
            })


"""
    TODO Find a better way to log requests.Response objects
"""
def _logResponse( r ):
    logging.debug("<<< Response : %s\tbody: %s", repr(r), r.content )



class TransBot(Bot):
    """
        Sample bot that translates text.

        It only answers to messages containing defined keywords.
        It uses IBM Watson™ Language Translator (see API docs : https://cloud.ibm.com/apidocs/language-translator) to translate the text.
    """


    def __init__( self,
        chatter, ibmcloud_url, ibmcloud_apikey,
        keywords=[], keywords_files=[],
        languages=[], languages_file=None, locale=re.split(r'[_-]',locale.getlocale()[0]),
        shutdown_pattern=r'bye nicobot' ):
        """
            keywords: list of keywords that will trigger this bot (in any supported language)
            keywords_files: list of JSON files with each a list of keywords (or write into)
            languages: List of supported languages in this format : https://cloud.ibm.com/apidocs/language-translator#list-identifiable-languages
            languages_file: JSON file where to find the list of target languages (or write into)
            locale: overrides the default locale ; tuple like : ('en','GB')
            shutdown_pattern: a regular expression pattern that terminates this bot
            chatter: the backend chat engine
            ibmcloud_url (required): IBM Cloud API base URL (e.g. 'https://api.eu-de.language-translator.watson.cloud.ibm.com/instances/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx')
            ibmcloud_apikey (required): IBM Cloud API key (e.g. 'dG90byBlc3QgZGFucyBsYSBwbGFjZQo')
            store_path: Base directory where to cache files
        """

        self.ibmcloud_url = ibmcloud_url
        self.ibmcloud_apikey = ibmcloud_apikey
        self.chatter = chatter

        self.locale = locale
        self.languages = languages
        if languages_file:
            # Only after IBM credentials have been set can we retrieve the list of supported languages
            self.languages = self.loadLanguages(file=languages_file,locale=locale[0])
        # How many different languages to try to translate to
        self.tries = 5

        # After self.languages has been set, we can iterate over it to translate keywords
        kws = self.loadKeywords( keywords=keywords, files=keywords_files, limit=LIMIT_KEYWORDS )
        # And build a regular expression pattern with all keywords and their translations
        pattern = r'\b%s\b' % kws[0]
        for keyword in kws[1:]:
            pattern = pattern + r'|\b%s\b' % keyword
        # Built regular expression pattern that triggers an answer from this bot
        self.re_keywords = pattern
        # Regular expression pattern of messages that stop the bot
        self.re_shutdown = shutdown_pattern


    def loadLanguages( self, force=False, file=None, locale='en' ):
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
        # FIXME Since IBM API doesn't support an Accept-Language header to get the languages name in the locale, we need to query it again
        logging.debug(">>> GET %s, %s",url,repr(headers))
        r = requests.get(url, headers=headers, auth=('apikey',self.ibmcloud_apikey), timeout=TIMEOUT)
        _logResponse(r)

        if r.status_code == requests.codes.ok:
            languages_root = r.json()
            languages = languages_root['languages']

            # IBM Cloud always returns language names in english
            # So we need to translate them if the locale is different
            if locale != 'en':
                languages_names = [ l['name'] for l in languages ]
                translations = self.translate(languages_names,source='en',target=locale)
                logging.debug("Got the following translations for languages names : %s",repr(translations))
                # From my tests seems that IBM cloud returns the original text if it could not translate it
                # so the output list will always be the same size as the input one
                t = 0
                for language in languages:
                    language['name'] = translations['translations'][t]['translation']
                    t = t + 1

            # Save it for the next time
            if file:
                try:
                    logging.debug("Saving languages to %s..." % file)
                    with open(file,'w') as f:
                        json.dump(languages_root,f)
                except:
                    logging.exception("Could not save the languages list to %s" % file)
                    pass
            else:
                logging.debug("Not saving languages as no file was given")

            return languages
        else:
            r.raise_for_status()


    def loadKeywords( self, keywords=[], files=[], limit=None ):
        """
            Generates a list of translations from a list of keywords.

            Requires self.languages to be filled before !

            If 'keywords' is not empty, will download the translations from IBM Cloud
            and if a single 'file' was given, will save them into it.
            Otherwise, will read from all the given 'files'
        """

        # TODO It starts with the same code as in loadLanguages : make it a function

        kws = []

        # Gets the list from a local file
        if len(keywords) == 0:
            for file in files:
                logging.debug("Reading from %s..." % file)
                # May throw an error
                with open(file,'r') as f:
                    kws = kws + json.load(f)
            logging.debug("Read keyword list : %s",repr(kws))
            return kws

        # TODO remove duplicates
        for keyword in keywords:
            logging.debug("Init %s...",keyword)
            kws = kws + [ keyword ]

            for lang in self.languages:
                # For tests, in order not to use all credits, we can limit the number of calls here
                if limit and len(kws) >= limit:
                    break
                try:
                    translation = self.translate( [keyword], target=lang['language'] )
                    if translation:
                        for t in translation['translations']:
                            translated = t['translation'].rstrip()
                            logging.debug("Adding translation %s in %s for %s", t, lang, keyword)
                            kws = kws + [ translated ]
                except:
                    logging.exception("Could not translate %s into %s", keyword, repr(lang))
                    pass
        logging.debug("Keywords : %s", repr(kws))

        # TODO ? Save the translations for each keyword into a separate file ?
        if files and len(files) == 1:
            try:
                logging.debug("Saving keywords translations into %s...", files[0])
                with open(files[0],'w') as f:
                    json.dump(kws,f)
            except:
                logging.exception("Could not save keywords translations into %s", files[0])
                pass
        else:
            logging.debug("Not saving keywords as a (single) file was not given")

        return kws


    def translate( self, messages, target, source=None ):
        """
            Translates a given list of messages.

            target: Target language short code (e.g. 'en')
            source: Source language short code ; if not given will try to guess

            Returns the full JSON translation as per the IBM cloud service or None if no translation could be found.
        """

        # curl -X POST -u "apikey:{apikey}" --header "Content-Type: application/json" --data "{\"text\": [\"Hello, world! \", \"How are you?\"], \"model_id\":\"en-es\"}" "{url}/v3/translate?version=2018-05-01"
        url = "%s/v3/translate?version=2018-05-01" % self.ibmcloud_url
        body = {
            "text": messages,
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
            return r.json()
        # A 404 can happen if there is no translation available
        elif r.status_code == requests.codes.not_found:
            return None
        else:
            r.raise_for_status()


    def formatTranslation( self, translation, target ):
        """
            Common decoration of translated messages

            transation = the result of translate()
            target = reminder of which target language was asked (does not appear in the response of translate())
        """

        text = translation['translations'][0]['translation']
        try:
            # Note : translation['detected_language'] is the detected source language, if guessed
            lang_emoji = flag.flag(target)
        except ValueError:
            lang_emoji= "🏳️‍🌈"
        answer = "%s %s" % (text,lang_emoji)
        return i18n.t('all_messages',message=answer)


    def identifyLanguage( self, language_name ):
        """
            Finds the language code from its name
        """
        # TODO should be at 'trace' level
        logging.debug("identifyLanguage(%s)",language_name)

        # First checks if this is already the language's code (more accurate)
        if language_name in [ l['language'] for l in self.languages ]:
            logging.debug("Identified language is already a code : %s",language_name)
            return language_name
        # Else, really try with the language's name
        else:
            matching_names = [ l for l in self.languages if re.search(language_name.strip(),l['name'],re.IGNORECASE) ]
            logging.debug("Identified languages by name : %s",matching_names)
            if len(matching_names) > 0:
                # Only take the first one
                return matching_names[0]['language']
            else:
                logging.warning("Could not identify language %s",language_name)
                return None


    def onMessage( self, message ):
        """
            Called by self.chatter whenever a message hsa arrived :
            if the given message contains any of the keywords in any language,
            will answer with a translation in a random language
            including the flag of the random language.

            message: A plain text message
            Returns the crafted translation
        """
        logging.debug("onMessage(%s)",message)

        # Preparing the 'translate a message' case
        to_lang = self.locale[0]
        matched_translate = re.search( i18n.t('translate'), message.strip(), flags=re.IGNORECASE )
        # Case where the target language is given
        if matched_translate:
            logging.debug("Detected 'translate a message with target' case")
            to_lang = self.identifyLanguage( matched_translate.group('language') )
            logging.debug("Found target language in message : %s"%to_lang)
        # Case where the target language is not given ; we will simply use the current locale
        else:
            matched_translate = re.search( i18n.t('translate_default_locale'), message.strip(), flags=re.IGNORECASE )
            if matched_translate:
                logging.debug("Detected 'translate a message' case")

        ###
        #
        # Case 'shutdown'
        #
        # FIXME re.compile((i18n.t('Shutdown'),re.IGNORECASE).search(message) does not work
        # as expected so we use re.search(...)
        if re.search( self.re_shutdown, message, re.IGNORECASE ):
            logging.debug("Shutdown asked")
            self.chatter.stop()

        ###
        #
        # Case 'translate a message'
        #
        elif matched_translate:
            if to_lang:
                translation = self.translate( [matched_translate.group('message')],target=to_lang )
                logging.debug("Got translation : %s",repr(translation))
                if translation and len(translation['translations'])>0:
                    answer = self.formatTranslation(translation,target=to_lang)
                    logging.debug(">> %s" % answer)
                    self.chatter.send(answer)
                else:
                    # TODO Make translate throw an error with details
                    logging.warning("Did not get a translation in %s for %s",to_lang,message)
                    self.chatter.send( i18n.t('all_messages',message=i18n.t('IDontKnow')) )
            else:
                logging.warning("Could not identify target language in %s",message)
                self.chatter.send( i18n.t('all_messages',message=i18n.t('IDontKnow')) )

        ###
        #
        # Case 'answer to keywords'
        #
        elif re.search( self.re_keywords, message, flags=re.IGNORECASE ):

            # Selects a few random target languages each time
            langs = random.choices( self.languages, k=self.tries )

            for lang in langs:
                # Gets a translation in this random language
                translation = self.translate( [message], target=lang['language'] )
                logging.debug("Got translation : %s",repr(translation))
                if translation and len(translation['translations'])>0:
                    answer = self.formatTranslation(translation,target=lang['language'])
                    logging.debug(">> %s" % answer)
                    self.chatter.send(answer)
                    # Returns as soon as one translation was done
                    return
                else:
                    pass

            logging.warning("Could not find a translation in %s for %s",repr(langs),message)

        else:
            logging.debug("Message did not match any known pattern")


    def onExit( self ):

        goodbye = i18n.t('Goodbye')
        if goodbye and goodbye.strip():
            sent = self.chatter.send( i18n.t('all_messages',message=goodbye) )
        else:
            logging.debug("No 'Goodbye' text : nothing was sent")


    def run( self ):
        """
            Starts the bot :

            1. Sends a hello message
            2. Waits for messages to translate
        """

        hello = i18n.t('Hello')
        if hello and hello.strip():
            self.chatter.send( i18n.t('all_messages',message=hello) )
        else:
            logging.debug("No 'Hello' text : nothing was sent")
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
    parser.add_argument("--keywords-file", dest="keywords_files", action="append", help="File to load from and write keywords to")
    parser.add_argument('--locale', '-l', dest='locale', default=config.locale, help="Change default locale (e.g. 'fr_FR')")
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
    parser.add_argument('--stealth', dest='stealth', action="store_true", default=config.stealth, help="Activate stealth mode on any chosen chatter")
    # Signal-specific arguments
    parser.add_argument('--signal-cli', dest='signal_cli', default=config.signal_cli, help="Path to `signal-cli` if not in PATH")
    parser.add_argument('--signal-stealth', dest='signal_stealth', action="store_true", default=config.signal_stealth, help="Activate Signal chatter's specific stealth mode")

    #
    # 1st pass only matters for 'bootstrap' options : configuration file and logging
    #
    parser.parse_args(namespace=config)

    # Logging configuration
    try:
        # Before Python 3.4 and back since 3.4.2 we can simply pass a level name rather than a numeric value (Yes !)
        # Otherwise manually parsing textual log levels was not clean IMHO anyway : https://docs.python.org/2/howto/logging.html#logging-to-a-file
        logLevel = logging.getLevelName(config.verbosity.upper())
        # Logs are output to stderr ; stdout is reserved to print the answer(s)
        logging.basicConfig(level=logLevel, stream=sys.stderr)
    except ValueError:
    	raise ValueError('Invalid log level: %s' % config.verbosity)
    logging.debug( "Configuration for bootstrap : %s", repr(vars(config)) )

    # Loads the config file that will be used to lookup some missing parameters
    if not config.config_file:
        config.config_file = os.path.join(config.config_dir,"config.yml")
        logging.debug("Using default config file : %s "%config.config_file)
    try:
        with open(config.config_file,'r') as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            try:
                # This is the required syntax in newer pyyaml distributions
                dictConfig = yaml.load(file, Loader=yaml.FullLoader)
            except:
                # Some systems (e.g. raspbian) ship with an older version of pyyaml
                dictConfig = yaml.load(file)
            logging.debug("Successfully loaded configuration from %s : %s" % (config.config_file,repr(dictConfig)))
            config.__dict__.update(dictConfig)
    except Exception as e:
        logging.debug(e, exc_info=True)
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
    # e.g. if config.locale is 'en_US' we split it into : ['en', 'US'] ; dash separator is the RFC norm '-', but underscore '_' is used with Python
    lang = re.split( r'[_-]', config.locale )
    # See https://pypi.org/project/python-i18n/
    # FIXME Manually sets the locale : how come a Python library named 'i18n' doesn't take into account the Python locale by default ?
    i18n.set('locale',lang[0])
    logging.debug("i18n locale : %s"%i18n.get('locale'))
    i18n.set('filename_format', 'i18n.{locale}.{format}')    # Removing the namespace from keys is simpler for us
    i18n.set('error_on_missing_translation',True)
    i18n.load_path.append(config.config_dir)

    # These MUST be instanciated AFTER i18n has been configured !
    try:
        i18n.t('all_messages',message="")
    except:
        i18n.add_translation('all_messages',r'%{message}')
    if not config.shutdown:
        config.shutdown = i18n.t('Shutdown')

    if not config.ibmcloud_url:
        raise ValueError("Missing required parameter : --ibmcloud-url")
    if not config.ibmcloud_apikey:
        raise ValueError("Missing required parameter : --ibmcloud-apikey")

    # config.keywords is used if given
    # else, check for an existing keywords_file
    if len(config.keywords_files) == 0:
        # As a last resort, use 'keywords.json' in the config directory
        config.keywords_files = [ os.path.join(config.config_dir,'keywords.json') ]
    # Convenience check to better warn the user and allow filenames relative to config_dir
    if not config.keywords:
        found_keywords_files = []
        for keywords_file in config.keywords_files:
            relative_filename = os.path.join(config.config_dir,keywords_file)
            winners = filter_files( [keywords_file, relative_filename], should_exist=True, fallback_to=None )
            if len(winners) > 0:
                found_keywords_files = found_keywords_files + winners
        if len(found_keywords_files) > 0:
            config.keywords_files = found_keywords_files
        else:
            raise ValueError("Could not open any keywords file in %s : please generate with --keywords first or create the file indicated with --keywords-file"%repr(config.keywords_files))

    # Finds an existing languages_file
    # By default, uses 'languages.<lang>.json' or 'languages.json' in the config directory
    config.languages_file = filter_files( [
        config.languages_file,
        os.path.join( config.config_dir, "languages.%s.json"%lang[0] ),
        os.path.join( config.config_dir, 'languages.json' ) ],
        should_exist=True,
        fallback_to=1 )[0]
    # Convenience check to better warn the user
    if not config.languages_file:
        raise ValueError("Missing language file : please use only --languages-file to generate it automatically or --language for each target language")

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
            signal_cli=config.signal_cli,
            stealth=config.signal_stealth)
    # By default (or if backend == "console"), will read from stdin or a given file and output to console
    else:
        chatter = ConsoleChatter(config.input_file,sys.stdout)

    if config.stealth:
        chatter = StealthChatter(chatter)

    #
    # Real start
    #

    TransBot(
        keywords=config.keywords, keywords_files=config.keywords_files,
        languages_file=config.languages_file,
        locale=lang,
        ibmcloud_url=config.ibmcloud_url, ibmcloud_apikey=config.ibmcloud_apikey,
        shutdown_pattern=config.shutdown,
        chatter=chatter
        ).run()
