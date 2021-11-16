from .db import get_db, getIDCol, getCSVCols

def processDataExtensionBatch(batch):
    ids, props = tuple(batch[x] for x in ('ids', 'properties'))
    names = {p['id'] for p in props}
    cols = {colnm: nm for colnm, nm in getCSVCols() if colnm in names}
    idcol = getIDCol()


    db = get_db()
    cur = db.cursor()
    # Could use some defensiveness in generating this SQL
    sql = "SELECT %s,%s FROM data WHERE %s in (%s)" % (idcol, ','.join(cols.keys()), idcol, ','.join('?' * len(ids)))
    cur.execute(sql, ids)
    rows = dict()
    for row in cur:
        rows[row[idcol]] = {col: [{'str': row[col]}] for col in cols}

    meta = [dict(id=p['id'], name=cols[p['id']]) for p in props]

    return dict(meta=meta, rows=rows)
