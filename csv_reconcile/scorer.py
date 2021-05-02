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


def scoreMatch(left, right, **scoreOptions):
    '''Score fuzzy match score between left and right'''
    raise RuntimeError('scoreMatch(left,right) -> float must be implemented')


def normalizeWord(word, **scoreOptions):
    '''
    Preprocess column being reconciled for the match calculation.
    Return a tuple with the same number of elements as returned by getNormalizedFields()
    '''
    raise RuntimeError(
        'normalizeWord(word, **options) -> tuple must be implemented')


def normalizeRow(word, row, **scoreOptions):
    '''
    Preprocess column being reconciled against for the match calculation.
    Return a tuple with the same number of elements as returned by getNormalizedFields()
    Defaults to using the same normalization as normalizeWord().
    '''
    return normalizeWord(word, **scoreOptions)


def valid(normalizedFields):
    '''Optionally validate column before performing match calculation'''
    return True


# [[https://reconciliation-api.github.io/specs/latest/#reconciliation-query-responses]]
def features(word, row, **scoreOptions):
    '''
    Takes the queryString and the normalized row and calculates features.
    The calculation is disabled by default.
    '''
    # This is just a dummy result since features are disabled by default.
    return [dict(id="someid", value=15), dict(id="someotherid", value=19)]


features.disabled = True
