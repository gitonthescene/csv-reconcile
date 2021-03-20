from .db import get_db
from normality import normalize
from collections import defaultdict

try:
    # Cython if it exists
    from csv_reconcile.cutils import getDiceCoefficient
except:
    from csv_reconcile.utils import getDiceCoefficient


def processQueryBatch(batch, limit=None, threshold=0.0, stopwords=None):
    '''
    Go through db looking for words with bigrams who score positively
    '''
    bigrams = dict()
    for qid, req in batch.items():
        queryStr = req['query']
        bigrams[qid] = makeBigrams(queryStr, stopwords=stopwords)

    # Better to pull these off an sqlite store
    db = get_db()

    cur = db.cursor()
    cur.execute('SELECT bigrams,word,id from reconcile')
    picks = defaultdict(list)
    for row in cur:
        if not row['bigrams']:
            continue

        for qid, req in batch.items():
            qBigrams = bigrams[qid]

            # Should ensure that these bigrams are ascii, ideally with no escaping
            score = getDiceCoefficient(qBigrams.encode('utf-8'),
                                       row['bigrams'].encode('utf-8'))
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


# [[https://en.wikipedia.org/wiki/Stop_word]]
def makeBigrams(word, stopwords=None):
    '''
    Normalize set of bigrams into an ordered string to aid processing
    '''
    # Should probably allow stop words
    # Should probably strip of spaces(?) and punctuation
    process = normalize(word)
    if stopwords:
        process = ' '.join(w for w in process.split() if w not in stopwords)
    return ''.join(
        sorted(set(process[i:i + 2] for i in range(len(process) - 1))))
