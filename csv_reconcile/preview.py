from .db import get_db, getCSVCols, getIDCol


def getEntity(entity_id):
    id_col = getIDCol()
    cols = dict(getCSVCols())

    cur = get_db().cursor()
    cur.execute(f"SELECT * FROM data WHERE {id_col}=? LIMIT 1", (entity_id,))
    row = cur.fetchone()
    if not row:
        return None
    return {cols[col]: value for col, value in zip(row.keys(), row)}
