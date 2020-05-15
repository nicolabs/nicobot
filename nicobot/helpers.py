# -*- coding: utf-8 -*-

"""
    Helper functions
"""

import logging


# Adds a log level finer than DEBUG
TRACE = 5
logging.addLevelName(TRACE,'TRACE')


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
