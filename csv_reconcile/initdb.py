from flask import current_app
import csv
from collections import defaultdict
from itertools import count

from .db import get_db, normalizeDBcol

from importlib.resources import read_text
import csv_reconcile
from . import scorer


def initDataTable(db, colnames, idcol):
    cols = []
    cnts = defaultdict(count)
    for col in colnames:
        slug = normalizeDBcol(col)
        slug = f'{slug}{next(cnts[slug])}'
        if col == idcol:
            cols.append('%s TEXT PRIMARY KEY' % (slug,))
        else:
            cols.append('%s TEXT NOT NULL' % (slug,))

        db.execute('INSERT INTO datacols VALUES (?,?,?)',
                   (col, slug, 1 if col == idcol else 0))

    # create data table with the contents of the csv file
    createSQL = 'CREATE TABLE data (\n  %s\n)'
    db.execute(createSQL % (',\n  '.join(cols),))


def initReconcileTable(db, colnames):
    create = [
        'CREATE TABLE reconcile (\n  id TEXT PRIMARY KEY,\n  word TEXT NOT NULL'
    ]
    for col in colnames:
        create.append('%s TEXT NOT NULL' % (col,))

    # create data table with the contents of the csv file
    db.execute(',\n  '.join(create) + '\n)')


def init_db(db,
            csvfilenm,
            idcol,
            searchcol,
            csvencoding=None,
            scoreOptions=None,
            csvkwargs=None):

    enckwarg = dict()
    if csvencoding:
        enckwarg['encoding'] = csvencoding

    schema = read_text(csv_reconcile, 'schema.sql')
    db.executescript(schema)

    csvkwargs = {} if csvkwargs is None else csvkwargs

    with db:
        # Create a table with ids (as PRIMARY ID), words and bigrams
        with open(csvfilenm, newline='', **enckwarg) as csvfile:
            reader = csv.reader(csvfile, **csvkwargs)
            header = next(reader)

            # Throws if col doesn't exist
            searchidx = header.index(searchcol)
            ididx = header.index(idcol)

            normalizedFields = scorer.getNormalizedFields()
            initDataTable(db, header, idcol)
            initReconcileTable(db, normalizedFields)

            datavals = ','.join('?' * len(header))

            for row in reader:
                if len(row) != len(header): continue
                mid = row[ididx]
                word = row[searchidx]
                matchFields = scorer.normalizeRow(word, row, **scoreOptions)
                db.execute(
                    "INSERT INTO reconcile VALUES (%s)" %
                    (','.join('?' * (2 + len(normalizedFields))),),
                    (mid, word) + tuple(matchFields))

                db.execute("INSERT INTO data VALUES (%s)" % (datavals), row)


def init_db_with_context(csvfilenm, idcol, searchcol):
    db = get_db()
    csvkwargs = current_app.config.get('CSVKWARGS', {})
    scoreOptions = current_app.config['SCOREOPTIONS']
    csvencoding = current_app.config.get('CSVENCODING', None)

    return init_db(db,
                   csvfilenm,
                   idcol,
                   searchcol,
                   csvencoding=csvencoding,
                   csvkwargs=csvkwargs,
                   scoreOptions=scoreOptions)
