import logging

DATABASE = 'csvreconcile.db'

CSVKWARGS = dict(delimiter='\t')

# CSVENCODING='utf-8-sig'

LIMIT = 10  # At most 10 matches per query

THRESHOLD = 30.0  # At least a 30% match

LOGLEVEL = logging.NOTSET

SCOREOPTIONS = {}
