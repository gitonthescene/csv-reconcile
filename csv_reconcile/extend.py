from flask import current_app
from .db import get_db


def getCSVCols():
    csvcols = current_app.config['CSVCOLS']
    db = get_db()
    cur = db.cursor()
    cur.execute("select * from datacols")
    return [(row['colname'], row['name'])
            for row in cur
            if row['name'] not in csvcols]


def processDataExtensionBatch(batch):
    idcol, _ = current_app.config['CSVCOLS']
    ids, props = tuple(batch[x] for x in ('ids', 'properties'))
    cols = tuple(p['id'] for p in props)
    db = get_db()
    cur = db.cursor()

    # Could use some defensiveness in generating this SQL
    cur.execute(
        "SELECT %s,%s from data where %s in (%s)" %
        (idcol, ','.join(cols), idcol, ','.join('?' * len(ids))), ids)

    meta = [{'id': col, 'name': col} for col in cols]
    rows = dict()
    for row in cur:
        rows[row[idcol]] = dict((col, [{'str': row[col]}]) for col in cols)

    return dict(meta=meta, rows=rows)
