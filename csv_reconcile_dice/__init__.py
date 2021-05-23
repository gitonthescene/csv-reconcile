from csv_reconcile import scorer
from normality import normalize

try:
    # Cython if it exists
    from .cutils import getDiceCoefficient
except:
    from .utils import getDiceCoefficient


# [[https://en.wikipedia.org/wiki/Stop_word]]
def makeBigrams(word, **scoreOptions):
    '''
    Normalize set of bigrams into an ordered string to aid processing
    '''
    # Should probably allow stop words
    # Should probably strip of spaces(?) and punctuation
    process = normalize(word)
    stopwords = scoreOptions.get('stopwords', None)
    if stopwords:
        process = ' '.join(w for w in process.split() if w not in stopwords)

    return ''.join(
        sorted(set(process[i:i + 2] for i in range(len(process) - 1))))


@scorer.register
def getNormalizedFields():
    return ('bigrams',)


@scorer.register
def processScoreOptions(options):
    if not options:
        return

    options['stopwords'] = [w.lower() for w in options['stopwords']]


@scorer.register
def scoreMatch(left, right, **scoreOptions):
    return getDiceCoefficient(left[0].encode('utf-8'), right[0].encode('utf-8'))


@scorer.register
def normalizeWord(word, **scoreOptions):
    return (makeBigrams(word, **scoreOptions),)


@scorer.register
def valid(normalizedFields):
    if not normalizedFields[0]:
        return False
    return True
