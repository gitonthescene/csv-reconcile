from .db import get_db
from normality import normalize
try:
    # Cython if it exists
    from csv_reconcile.cutils import getDiceCoefficient
except:
    from csv_reconcile.utils import getDiceCoefficient


def searchFor(queryStr, limit=None, threshold=0.0):
    '''
    Go through db looking for words with bigrams who score positively
    '''

    # Better to pull these off an sqlite store
    db = get_db()

    # Normalize the set of bigrams to make processing easier
    qBigrams = makeBigrams(queryStr)

    cur = db.cursor()
    cur.execute('SELECT bigrams,word,id from reconcile')
    pick = []
    for row in cur:
        # Should ensure that these bigrams are ascii, ideally with no escaping
        score = getDiceCoefficient(qBigrams.encode('utf-8'),
                                   row['bigrams'].encode('utf-8'))
        if score > threshold:
            pick.append((row, score))

    res = []
    cnt = 0
    for row, score in sorted(pick, key=lambda x: -x[1]):
        cnt += 1
        if limit and cnt > limit:
            break

        # Match when exact.  More heuristics below
        res.append(
            dict(id=row['id'],
                 name=row['word'],
                 score=score,
                 match=(queryStr == row['word'])))

    # Make match if only one
    if len(res) == 1:
        res[0]['match'] = True

    # Maybe match if there is a wide gap in score between first match and second?

    return res


# [[https://en.wikipedia.org/wiki/Stop_word]]
def makeBigrams(word):
    '''
    Normalize set of bigrams into an ordered string to aid processing
    '''
    # Should probably allow stop words
    # Should probably strip of spaces(?) and punctuation
    process = normalize(word)
    return ''.join(
        sorted(set(process[i:i + 2] for i in range(len(process) - 2))))
