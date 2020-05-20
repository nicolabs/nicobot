# -*- coding: utf-8 -*-

"""
    Helper functions
"""

import sys
import logging


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
