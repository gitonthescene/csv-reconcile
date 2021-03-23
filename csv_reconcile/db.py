import sqlite3
import os.path
from flask import current_app, g

from normality import slugify


def normalizeDBcol(col):
    return slugify(col).replace('-', '_')


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
