import click
from flask import current_app
from flask.cli import with_appcontext
import csv
from .score import makeBigrams
from .db import get_db, close_db


def init_db():
    db = get_db()
    idcol, searchcol = current_app.config['CSVCOLS']
    csvfilenm = current_app.config['CSVFILE']
    kwargs = current_app.config.get('CSVKWARGS', {})
    csvencoding = current_app.config.get('CSVENCODING', None)
    enckwarg = dict()
    if csvencoding:
        enckwarg['encoding'] = csvencoding

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

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


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
