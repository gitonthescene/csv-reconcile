import os.path
import sqlite3

from flask import current_app, g
from normality import slugify


def normalizeDBcol(col):
    return slugify(col).replace('-', '_')


def getCSVCols():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM datacols")
    return [(row['colname'], row['name']) for row in cur]


def getIDCol():
    cur = get_db().cursor()

    cur.execute("SELECT colname FROM datacols WHERE isid == 1")
    res = cur.fetchall()
    if len(res) != 1:
        raise RuntimeError("database not properly initialized")
    return res[0]['colname']


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(os.path.join(current_app.instance_path,
                                            current_app.config['DATABASE']),
                               detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()
