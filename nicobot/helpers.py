# -*- coding: utf-8 -*-

"""
    Helper functions
"""

import logging
import os
import sys
import yaml


# Adds a log level finer than DEBUG
TRACE = 5
logging.addLevelName(TRACE,'TRACE')


def configure_logging( level=None, debug=None ):
    """
        Sets default logging preferences for this module

        if debug=True, overrides level with DEBUG
    """

    if debug:
        logLevel = logging.DEBUG
    else:
        try:
            # Before Python 3.4 and back since 3.4.2 we can simply pass a level name rather than a numeric value (Yes !)
            # Otherwise manually parsing textual log levels was not clean IMHO anyway : https://docs.python.org/2/howto/logging.html#logging-to-a-file
            logLevel = logging.getLevelName(level.upper())
        except ValueError:
        	raise ValueError('Invalid log level: %s' % level)

    # Logs are output to stderr ; stdout is reserved to print the answer(s)
    logging.basicConfig(level=logLevel, stream=sys.stderr, format='%(asctime)s\t%(levelname)s\t%(message)s')


def filter_files( files, should_exist=False, fallback_to=None ):
    """
        files: a list of filenames / open files to filter
        should_exist: filters out non-existing files
        fallback_to: if the result would be an empty list, add the entry with this index in the result ; ignored if None
        Returns : a list with only the files that passed the filters
    """

    found = []
    for file in files:
        if should_exist:
            try:
                with open(file,'r') as f:
                    pass
            except:
                continue
        found = found + [file]

    if len(found) == 0 and fallback_to is not None:
        return files[fallback_to:fallback_to+1]

    return found


def parse_args_2pass( parser, args, config ):
    """
        Wrapper around argparse's ArgumentParser.parse_args that makes two passes :

        1. the first one to identify a configuration file and load defaults from it
        2. the second one to parse other command-line parameters falling back to defaults from the config file for missing parameters

        It also takes care of logging configuration, which is considered part of the "bootstrap" sequence.
    """

    #
    # 1st pass only matters for 'bootstrap' options : configuration file and logging
    #
    # Note : we don't let the parse_args method merge the Namespace into config yet,
    # because it would not be possible to make the difference between the default values
    # and the ones explictely given by the user
    # This is usefull for instance to throw an exception if a file given by the user doesn't exist, which is different than the default filename
    # 'config' is therefore the defaults overriden by user options while 'ns' has only user options
    ns = parser.parse_args(args=args)

    # Logging configuration
    configure_logging(ns.verbosity,debug=ns.debug)
    logging.debug( "Configuration for bootstrap : %s", repr(vars(ns)) )

    # Fills the config with user-defined default options from a config file
    try:
        # Allows config_file to be relative to the config_dir
        config.config_file = filter_files(
            [ns.config_file,
            os.path.join(ns.config_dir,"config.yml")],
            should_exist=True,
            fallback_to=1 )[0]
        logging.debug("Using config file %s",config.config_file)
        with open(config.config_file,'r') as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            try:
                # This is the required syntax in newer pyyaml distributions
                dictConfig = yaml.load(file, Loader=yaml.FullLoader)
            except AttributeError:
                # Some systems (e.g. raspbian) ship with an older version of pyyaml
                dictConfig = yaml.load(file)
            logging.debug("Successfully loaded configuration from %s : %s" % (config.config_file,repr(dictConfig)))
            config.__dict__.update(dictConfig)
    except OSError as e:
        # If it was a user-set option, stop here
        if ns.config_file == config.config_file:
            raise e
        else:
            logging.debug("Could not open %s ; no config file will be used",config.config_file)
            logging.debug(e, exc_info=True)
            pass
    # From here the config object has only the default values for all configuration options

    #
    # 2nd pass parses all options
    #
    # Updates again the existing config object with all parsed options
    config = parser.parse_args(args=args,namespace=config)
    # From the bootstrap parameters, only logging level may need to be read again
    configure_logging(config.verbosity,debug=config.debug)
    logging.debug( "Final configuration : %s", repr(vars(config)) )

    return config
