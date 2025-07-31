"""Default settings as a python module."""
import logging

DATABASE = 'csvreconcile.db'

LIMIT = 10  # At most 10 matches per query

THRESHOLD = 30.0  # At least a 30% match

LOGLEVEL = logging.NOTSET

SCOREOPTIONS = {}
