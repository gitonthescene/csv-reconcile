from .db import get_db, getIDCol, getCSVCols


def processDataExtensionBatch(batch):
    ids, props = tuple(batch[x] for x in ('ids', 'properties'))
    names = {p['id'] for p in props}
    cols = {colnm: nm for colnm, nm in getCSVCols() if nm in names}
    idcol = getIDCol()

    db = get_db()
    cur = db.cursor()
    # Could use some defensiveness in generating this SQL
    cur.execute(
        "SELECT %s,%s FROM data WHERE %s in (%s)" %
        (idcol, ','.join(cols.keys()), idcol, ','.join('?' * len(ids))), ids)

    rows = dict()
    for row in cur:
        rows[row[idcol]] = {cols[col]: [{'str': row[col]}] for col in cols}

    meta = [dict(id=p['id'], name=p['id']) for p in props]

    return dict(meta=meta, rows=rows)
