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
import urllib.request

# Own classes
from .helpers import *
from .bot import Bot
from .bot import ArgsHelper as BotArgsHelper
from .console import ConsoleChatter
from .jabber import JabberChatter
from .jabber import arg_parser as jabber_arg_parser
from .signalcli import SignalChatter
from .signalcli import ArgsHelper as SignalArgsHelper
from .stealth import StealthChatter



# Default timeout for requests in seconds
# Note : More than 10s recommended (30s ?) on IBM Cloud with a free account
TIMEOUT = 60

# Set to None to translate keywords in all available languages
# Set to something > 0 to limit the number of translations for the keywords (for tests)
LIMIT_KEYWORDS = None

# See https://github.com/nicolabs/nicobot/issues/8
# Description : https://unicode.org/reports/tr35/#Likely_Subtags
# Original XML version : http://cldr.unicode.org/index/cldr-spec/language-tag-equivalences
# This is the URL to the JSON version
LIKELY_SUBTAGS_URL = "https://raw.githubusercontent.com/unicode-cldr/cldr-core/master/supplemental/likelySubtags.json"


# Default configuration (some defaults still need to be set up after command line has been parsed)
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
            'languages_likely': None,
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


def sanitizeNotPattern( string ):
    """
        Returns a string that will only all 'non-word' characters escaped with backslash
        in order to use it in a regular expression pattern without including special character.

        We could just replace any character 'c' with '\c' but replacing only special characters keep it somewhat still readable.
    """
    return re.sub( r'([^\w])', '\\\\\\1', string )



class TransBot(Bot):
    """
        Sample bot that translates text.

        It only answers to messages containing defined keywords.
        It uses IBM Watson™ Language Translator (see API docs : https://cloud.ibm.com/apidocs/language-translator) to translate the text.
    """


    def __init__( self,
        chatter, ibmcloud_url, ibmcloud_apikey,
        keywords=[], keywords_files=[],
        languages=[], languages_file=None, languages_likely=None,
        locale=re.split(r'[_-]',locale.getlocale()[0]),
        shutdown_pattern=r'bye nicobot' ):
        """
            keywords: list of keywords that will trigger this bot (in any supported language)
            keywords_files: list of JSON files with each a list of keywords (or write into)
            languages: List of supported languages in this format : https://cloud.ibm.com/apidocs/language-translator#list-identifiable-languages
            languages_file: JSON file where to find the list of target languages (or write into)
            languages_likely: JSON URI where to find Unicode's likely subtags (or write into)
            locale: overrides the default locale ; tuple like : ('en','GB')
            shutdown_pattern: a regular expression pattern that terminates this bot
            chatter: the backend chat engine
            ibmcloud_url (required): IBM Cloud API base URL (e.g. 'https://api.eu-de.language-translator.watson.cloud.ibm.com/instances/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx')
            ibmcloud_apikey (required): IBM Cloud API key (e.g. 'dG90byBlc3QgZGFucyBsYSBwbGFjZQo')
            store_path: Base directory where to cache files
        """

        self.status = {'events':[]}

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

        self.likelyLanguages = self.loadLikelyLanguages(languages_likely)

        # After self.languages has been set, we can iterate over it to translate keywords
        kws = self.loadKeywords( keywords=keywords, files=keywords_files, limit=LIMIT_KEYWORDS )
        # And build a regular expression pattern with all keywords and their translations
        pattern = r'\b%s\b' % sanitizeNotPattern(kws[0])
        for keyword in kws[1:]:
            pattern = pattern + r'|\b%s\b' % sanitizeNotPattern(keyword)
        # Built regular expression pattern that triggers an answer from this bot
        self.re_keywords = pattern
        # Regular expression pattern of messages that stop the bot
        self.re_shutdown = shutdown_pattern


    def _logEvent( self, event ):

        self.status['events'].append(event)


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
                    language['name'] = translations['translations'][t]['translation'].strip()
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
                            translated = t['translation'].strip()
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


    def loadLikelyLanguages( self, file ):
        """
            Returns a dict from a Likely Subtags JSON structure in the given file.
            If the file cannot be read, will download it from LIKELY_SUBTAGS_URL and save it with the given filename.
        """

        try:
            logging.debug("Loading likely languages from %s",file)
            with open(file,'r') as f:
                return json.load(f)
        except:
            logging.debug("Downloading likely subtags from %s",LIKELY_SUBTAGS_URL)
            with urllib.request.urlopen(LIKELY_SUBTAGS_URL) as response:
                likelySubtags = response.read()
                logging.log(TRACE,"Got likely subtags : %s",repr(likelySubtags))
                # Saves it for the next time
                try:
                    logging.debug("Saving likely subtags into %s",file)
                    with open(file,'w') as f:
                        f.write(likelySubtags.decode())
                except:
                    logging.exception("Error saving the likely languages into %s",repr(file))
                return json.loads(likelySubtags)


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


    def languageToCountry( self, lang ):
        """
            Returns the most likely ISO 3361 country code from an (~ISO 639 or IBM-custom) language
            or the given 'lang' if no country code could be identified.

            lang : the language returned by IBM Translator service (is it ISO 639 ?)

            See https://github.com/nicolabs/nicobot/issues/8
            Likely subtags explanation and format :
            - https://unicode.org/reports/tr35/#Likely_Subtags
            - http://cldr.unicode.org/index/cldr-spec/language-tag-equivalences
        """
        try:
            aa_Bbbb_CC = self.likelyLanguages['supplemental']['likelySubtags'][lang]
            logging.log(TRACE,"Found likely subtags %s for language %s",aa_Bbbb_CC,lang)
            # The last part is the ISO 3361 country code
            return re.split( r'[_-]', aa_Bbbb_CC )[-1]
        except:
            logging.warning("Could not find a country code for %s : returning itself",lang, exc_info=True)
            return lang


    def formatTranslation( self, translation, target ):
        """
            Common decoration of translated messages

            transation = the result of translate()
            target = reminder of which target language was asked (does not appear in the response of translate())
        """

        text = translation['translations'][0]['translation'].strip()
        try:
            # Note : translation['detected_language'] is the detected source language, if guessed
            country = self.languageToCountry(target)
            lang_emoji = flag.flag(country)
        except ValueError:
            logging.debug("Error looking for flag %s",target,exc_info=True)
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
            Returns nothing
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
            self._logEvent({ 'type':'shutdown', 'message':message })
            self.chatter.stop()

        ###
        #
        # Case 'translate a message'
        #
        elif matched_translate:
            status_event = { 'type':'translate', 'message':message, 'target_lang':to_lang }
            self._logEvent(status_event)
            if to_lang:
                translation = self.translate( [matched_translate.group('message')],target=to_lang )
                logging.debug("Got translation : %s",repr(translation))
                status_event['translation'] = translation
                if translation and len(translation['translations'])>0:
                    answer = self.formatTranslation(translation,target=to_lang)
                    logging.debug(">> %s" % answer)
                    status_event['answer'] = answer
                    self.chatter.send(answer)
                else:
                    # TODO Make translate throw an error with details
                    logging.warning("Did not get a translation in %s for %s",to_lang,message)
                    answer = i18n.t('all_messages',message=i18n.t('IDontKnow'))
                    status_event['error'] = 'no_translation'
                    status_event['answer'] = answer
                    self.chatter.send(answer)
            else:
                logging.warning("Could not identify target language in %s",message)
                answer = i18n.t('all_messages',message=i18n.t('IDontKnow'))
                status_event['error'] = 'unknown_target_language'
                status_event['answer'] = answer
                self.chatter.send( i18n.t('all_messages',message=i18n.t('IDontKnow')) )

        ###
        #
        # Case 'answer to keywords'
        #
        elif re.search( self.re_keywords, message, flags=re.IGNORECASE ):

            status_translations = []
            status_event = { 'type':'keyword', 'message':message, 'translations':status_translations }
            self._logEvent( status_event )

            # Selects a few random target languages each time
            langs = random.choices( self.languages, k=self.tries )

            for lang in langs:
                # Gets a translation in this random language
                translation = self.translate( [message], target=lang['language'] )
                logging.debug("Got translation : %s",repr(translation))
                status_translation = { 'target_language':lang['language'], 'translation':translation }
                status_translations.append(status_translation)
                if translation and len(translation['translations'])>0:
                    answer = self.formatTranslation(translation,target=lang['language'])
                    logging.debug(">> %s" % answer)
                    status_translation['answer'] = answer
                    self.chatter.send(answer)
                    # Returns as soon as one translation was done
                    return
                else:
                    logging.debug("No translation for %s in %r",message,langs)
                    status_translation['error'] = 'no_translation'
                    pass

            logging.warning("Could not find a translation in %s for %s",repr(langs),message)

        else:
            logging.debug("Message did not match any known pattern")
            self._logEvent({ 'type':'ignored', 'message':message })


    def onExit( self ):

        logging.debug("Exiting...")
        status_shutdown = { 'type':'shutdown' }
        self._logEvent(status_shutdown)

        # TODO Better use gettext in the end
        try:
            goodbye = i18n.t('Goodbye')
            if goodbye and goodbye.strip():
                text = i18n.t('all_messages',message=goodbye)
                sent = self.chatter.send(text)
                status_shutdown['answer'] = text
                status_shutdown['timestamp'] = sent
            else:
                logging.debug("Empty 'Goodbye' text : nothing was sent")
        except KeyError:
            logging.debug("No 'Goodbye' text : nothing was sent")
            pass


    def run( self ):
        """
            Starts the bot :

            1. Sends a hello message
            2. Waits for messages to translate

            Returns the execution status of the run, as a dict : { 'events':[list_of_events] }
            with list_of_events the list of input / outputs that happened, for audit purposes
        """

        self.chatter.connect()

        # TODO Better using gettext, in the end
        try:
            hello = i18n.t('Hello')
            if hello and hello.strip():
                text = i18n.t('all_messages',message=hello)
                sent = self.chatter.send(text)
                self._logEvent({ 'type':'startup', 'answer':text, 'timestamp':sent })
            else:
                logging.debug("Empty 'Hello' text : nothing was sent")
        except KeyError:
            logging.debug("No 'Hello' text : nothing was sent")
            pass

        self.registerExitHandler()
        self.chatter.start(self)
        logging.debug("Chatter loop ended")
        return self.status



def run( args=sys.argv[1:] ):

    """
        A convenient CLI to play with this bot
    """

    config = Config()

    parser = argparse.ArgumentParser(
        parents=[ BotArgsHelper().parser(), jabber_arg_parser(), SignalArgsHelper().parser() ],
        description="A bot that reacts to messages with given keywords by responding with a random translation"
        )
    # Core arguments for this bot
    parser.add_argument("--keyword", "-k", dest="keywords", action="append", help="A keyword a bot should react to (will write them into the file specified with --keywords-file)")
    parser.add_argument("--keywords-file", dest="keywords_files", action="append", help="File to load from and write keywords to")
    parser.add_argument('--locale', '-l', dest='locale', default=config.locale, help="Change default locale (e.g. 'fr_FR')")
    parser.add_argument("--languages-file", dest="languages_file", help="File to load from and write languages to")
    parser.add_argument("--languages-likely", dest="languages_likely", default=config.languages_likely, help="URI to Unicode's Likely Subtags (best language <-> country matches) in JSON format")
    parser.add_argument("--shutdown", dest="shutdown", help="Shutdown keyword regular expression pattern")
    parser.add_argument("--ibmcloud-url", dest="ibmcloud_url", help="IBM Cloud API base URL (get it from your resource https://cloud.ibm.com/resources)")
    parser.add_argument("--ibmcloud-apikey", dest="ibmcloud_apikey", help="IBM Cloud API key (get it from your resource : https://cloud.ibm.com/resources)")

    #
    # Two-pass arguments parsing
    #
    config = parse_args_2pass( parser, args, config )
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

    # Finds a "likely language" file
    config.languages_likely = filter_files([
        config.languages_likely,
        os.path.join( config.config_dir, 'likelySubtags.json' ) ],
        should_exist=True,
        fallback_to=1 )[0]

    # Creates the chat engine depending on the 'backend' parameter
    chatter = BotArgsHelper.chatter(config)

    #
    # Real start
    #

    bot = TransBot(
        keywords=config.keywords, keywords_files=config.keywords_files,
        languages_file=config.languages_file, languages_likely=config.languages_likely,
        locale=lang,
        ibmcloud_url=config.ibmcloud_url, ibmcloud_apikey=config.ibmcloud_apikey,
        shutdown_pattern=config.shutdown,
        chatter=chatter
        )
    status_args = vars(config)
    # TODO Add an option to list the fields to obfuscate (nor not)
    for k in [ 'ibmcloud_apikey', 'jabber_password' ]:
        status_args[k] = '(obfuscated)'
    status_result = bot.run()
    status = { 'args':vars(config), 'result':status_result }
    # NOTE ensure_ascii=False + encode('utf-8').decode() is not mandatory but allows printing plain UTF-8 strings rather than \u... or \x...
    # NOTE default=repr is mandatory because some objects in the args are not serializable
    print( json.dumps(status,skipkeys=True,ensure_ascii=False,default=repr).encode('utf-8').decode(), file=sys.stdout, flush=True )
    # Still returns the full status for simpler handling in Python
    return status


if __name__ == '__main__':

    run()
