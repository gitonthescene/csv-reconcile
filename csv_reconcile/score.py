from collections import defaultdict
from . import scorer


def reconcileStrings(db, items, **kwargs):
    # Use index as query id
    batch = dict(enumerate({'query': s} for s in items))

    ret = processQueryBatch(db, batch, **kwargs)

    # Return as a list of pairs of query matched to result
    return list(zip(items, (res for _, res in sorted(ret.items()))))


def processQueryBatch(db, batch, limit=None, threshold=0.0, **scoreOptions):
    '''
    Go through db looking for words whose fuzzy match score positively
    '''
    hasFeatures = not getattr(scorer.features, "disabled", False)

    toMatchItems = dict()
    for qid, req in batch.items():
        queryStr = req['query']
        toMatchItems[qid] = scorer.normalizeWord(queryStr, **
                                                 scoreOptions) or queryStr

    # Better to pull these off an sqlite store

    cur = db.cursor()
    normalizedFields = scorer.getNormalizedFields()

    cur.execute('SELECT %s FROM reconcile' %
                (','.join(('word', 'id') + tuple(normalizedFields))))

    picks = defaultdict(list)
    for row in cur:
        compareTo = row[2:] if normalizedFields else row['word']
        if not scorer.valid(compareTo):
            continue

        for qid in batch.keys():
            toMatch = toMatchItems[qid]

            score = scorer.scoreMatch(toMatch, compareTo, **scoreOptions)
            if score is not None and score > threshold:
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

            if hasFeatures:
                features = scorer.features(queryStr, row)
                if features is not None:
                    res[-1]['features'] = features

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
