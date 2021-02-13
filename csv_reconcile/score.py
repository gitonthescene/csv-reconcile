from .db import get_db


# [[https://en.wikipedia.org/wiki/S%C3%B8rensen%E2%80%93Dice_coefficient]]
# Could speed this up using Cython
def getDiceCoefficient(bigram1, bigram2):
    '''
    Calculate the Dice coefficient from two normalized sets of bigrams
    '''
    l1 = len(bigram1)
    l2 = len(bigram2)
    i1 = i2 = cnt = 0

    while i1 < l1 and i2 < l2:
        b1 = bigram1[i1:i1 + 2]
        b2 = bigram2[i2:i2 + 2]
        if b1 == b2:
            cnt += 1
            i1 += 2
            i2 += 2
        elif b1 < b2:
            i1 += 2
        else:
            i2 += 2

    # length is twice the number of bigrams
    return 400.0 * cnt / (l1 + l2)


def searchFor(queryStr, limit=None, threshold=0.0):
    '''
    Go through db looking for words with bigrams who score positively
    '''

    # Better to pull these off an sqlite store
    db = get_db()

    # Normalize the set of bigrams to make processing easier
    qBigrams = makeBigrams(queryStr)

    cur = db.cursor()
    cur.execute('SELECT DISTINCT bigrams from reconcile')
    pick = []
    for row in cur:
        score = getDiceCoefficient(qBigrams, row['bigrams'])
        if score > threshold:
            pick.append((row['bigrams'], score))

    res = []
    cnt = 1
    for bigrams, score in sorted(pick, key=lambda x: -x[1]):
        cur.execute('SELECT id, word from reconcile where bigrams=?',
                    (bigrams,))

        for row in cur:
            cnt += 1
            if limit and cnt > limit:
                break

            # Match when exact.  Could have looser heuristics.
            res.append(
                dict(id=row['id'],
                     name=row['word'],
                     score=score,
                     match=(queryStr == row['word'])))
        else:
            continue
        break

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
    process = word.lower()
    return ''.join(
        sorted(set(process[i:i + 2] for i in range(len(process) - 2))))
