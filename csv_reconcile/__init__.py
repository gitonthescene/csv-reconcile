from flask import Flask, request, jsonify
from flask_cors import cross_origin
import logging
from .score import searchFor
from . import initdb
from . import default_settings
import json
import os.path
from contextlib import contextmanager
import time
import click

#------------------------------------------------------------------
# Implement reconciliation API
# [[https://reconciliation-api.github.io/specs/latest/]]
#------------------------------------------------------------------


@contextmanager
def Timer():
    t = time.perf_counter()
    print("start timer", flush=True)
    yield
    elapsed = time.perf_counter() - t
    print("Elapsed: %s" % (elapsed,))


def processQueryBatch(queryBatch, threshold=0.0, limit=None):
    res = dict()
    for qid, req in queryBatch.items():
        queryStr = req['query']
        limit = req.get('limit', limit)
        res[qid] = dict(
            result=searchFor(queryStr, limit=limit, threshold=threshold))

    return res


MANIFEST = {
    "versions": ["0.1"],
    "name": "CSV Reconcile",
    "identifierSpace": "http://localhost/csv_reconcile/ids",
    "schemaSpace": "http://localhost/csv_reconcile/schema"
}


def create_app(setup=None, config=None):
    app = Flask("csv-reconcile")
    # Could make dbname configurable
    # possibly better to roll THRESHOLD and LIMIT into one config called LIMITS
    app.config.from_object(default_settings)
    if config:
        app.config.from_pyfile(config)

    app.config.from_mapping(**setup)
    if 'MANIFEST' in app.config:
        MANIFEST.update(app.config['MANIFEST'])

    app.logger.setLevel(logging.INFO)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/reconcile', methods=['POST', 'GET'])
    @cross_origin()
    def acceptQuery():
        threshold = app.config.get('THRESHOLD', None)
        limit = app.config.get('LIMIT', None)
        queries = request.form.get('queries')
        if queries:
            queryBatch = json.loads(queries)

            app.logger.info(queryBatch)
            with Timer():
                ret = processQueryBatch(queryBatch,
                                        threshold=threshold,
                                        limit=limit)
            app.logger.info(ret)
            return ret
        else:
            return MANIFEST

    return app


@click.command()
@click.option('--config', help='config file')
@click.option('--init-db', is_flag=True, help='initialize the db')
@click.argument('csvfile')
@click.argument('idcol')
@click.argument('namecol')
def main(config, init_db, csvfile, idcol, namecol):
    app = create_app(dict(CSVFILE=csvfile, CSVCOLS=(idcol, namecol)), config)
    if init_db:
        with app.app_context():
            initdb.init_db()
            click.echo('Initialized the database.')

    app.run()
