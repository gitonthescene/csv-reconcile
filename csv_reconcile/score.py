from .db import get_db
from normality import normalize
from collections import defaultdict
from . import scorer

try:
    # Cython if it exists
    from csv_reconcile.cutils import getDiceCoefficient
except:
    from csv_reconcile.utils import getDiceCoefficient


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
def scoreMatch(left, right):
    return getDiceCoefficient(left[0].encode('utf-8'), right[0].encode('utf-8'))


@scorer.register
def normalizeWord(word, **scoreOptions):
    return (makeBigrams(word, **scoreOptions),)


@scorer.register
def valid(normalizedFields):
    if not normalizedFields[0]:
        return False
    return True


def processQueryBatch(batch, limit=None, threshold=0.0, **scoreOptions):
    '''
    Go through db looking for words whose fuzzy match score positively
    '''
    toMatchItems = dict()
    for qid, req in batch.items():
        queryStr = req['query']
        toMatchItems[qid] = scorer.normalizeWord(queryStr, **scoreOptions)

    # Better to pull these off an sqlite store
    db = get_db()

    cur = db.cursor()
    normalizedFields = scorer.getNormalizedFields()

    cur.execute('SELECT word,id,%s from reconcile' %
                (','.join(normalizedFields,)))

    picks = defaultdict(list)
    for row in cur:
        if not scorer.valid(row[2:]):
            continue

        for qid, req in batch.items():
            toMatch = toMatchItems[qid]

            score = scorer.scoreMatch(toMatch, row[2:])
            if score > threshold:
                picks[qid].append((row, score))

    ret = dict()
    for qid in batch:
        pick = picks[qid]
        lmt = batch[qid].get('limit', limit)
        queryStr = batch[qid]['query']

        res = []
        exacts = []
        cnt = 0
        for row, score in sorted(pick, key=lambda x: -x[1]):
            cnt += 1
            if lmt and cnt > lmt:
                break

            res.append(
                dict(id=row['id'], name=row['word'], score=score, match=False))

            if res[-1]['name'] == queryStr:
                exacts.append(res[-1])

        # Make match if only one
        if len(res) == 1:
            res[0]['match'] = True
        else:
            if len(exacts) == 1:
                exacts[0]['match'] = True

        # Maybe match if there is a wide gap in score between first match and second?
        ret[qid] = dict(result=res)

    return ret
