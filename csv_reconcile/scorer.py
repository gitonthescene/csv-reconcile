def register(func):
    '''
    Decorator for replacing functions in this module
    '''
    glbls = globals()
    glbls[func.__name__] = func
    return func


def getNormalizedFields():
    '''List of fields generated from reconciled column for the match calculation'''
    raise RuntimeError('getNormalizedFields() -> tuple must be implemented')


def processScoreOptions(options):
    '''Optionally modify configuration options passed in'''


def scoreMatch(left, right):
    '''Score fuzzy match score between left and right'''
    raise RuntimeError('scoreMatch(left,right) -> float must be implemented')


def normalizeWord(word, **scoreOptions):
    '''
    Preprocess reconciled column for the match calculation.
    Return a tuple with the same number of elements as returned by getNormalizedFields()
    '''
    raise RuntimeError(
        'normalizeWord(word, **options) -> tuple must be implemented')


def valid(normalizedFields):
    '''Optionally validate column before performing match calculation'''
    return True
