from flask import current_app
import csv
from .score import makeBigrams
from .db import get_db
from importlib.resources import read_text
import csv_reconcile


def init_db():
    db = get_db()
    idcol, searchcol = current_app.config['CSVCOLS']
    csvfilenm = current_app.config['CSVFILE']
    kwargs = current_app.config.get('CSVKWARGS', {})
    csvencoding = current_app.config.get('CSVENCODING', None)
    enckwarg = dict()
    if csvencoding:
        enckwarg['encoding'] = csvencoding

    schema = read_text(csv_reconcile, 'schema.sql')
    db.executescript(schema)

    with db:
        # Create a table with ids (as PRIMARY ID), words and bigrams
        with open(csvfilenm, newline='', **enckwarg) as csvfile:
            reader = csv.reader(csvfile, **kwargs)
            header = next(reader)

            # Throws if col doesn't exist
            searchidx = header.index(searchcol)
            ididx = header.index(idcol)

            for row in reader:
                mid = row[ididx]
                word = row[searchidx]
                bigrams = makeBigrams(word)
                db.execute("INSERT INTO reconcile VALUES (?,?,?)",
                           (mid, word, bigrams))
