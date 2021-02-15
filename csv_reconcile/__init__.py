from flask import Flask, request, jsonify
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


MANIFEST = {}


def create_app(setup=None, config=None):
    app = Flask("csv-reconcile")
    # Could make dbname configurable
    # possibly better to roll THRESHOLD and LIMIT into one config called LIMITS
    app.config.from_object(default_settings)
    if config:
        app.config.from_pyfile(config)

    app.config.from_mapping(**setup)
    MANIFEST.update((
        ("name", app.config['SERVICENAME']),
        ("versions", app.config['VERSIONS']),
        ("identifierSpace", app.config['IDSPACE']),
        ("schemaSpace", app.config['SCHEMASPACE']),
    ))
    if 'VIEW' in app.config:
        MANIFEST['view'] = app.config['VIEW']

    app.logger.setLevel(logging.INFO)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    def jsonpify(obj):
        """
        Like jsonify but wraps result in a JSONP callback if a 'callback'
        query param is supplied.
        """
        try:
            callback = request.args['callback']
            response = app.make_response("%s(%s)" % (callback, json.dumps(obj)))
            response.mimetype = "text/javascript"
            return response
        except KeyError:
            return jsonify(obj)

    @app.route('/reconcile', methods=['POST', 'GET'])
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
            return jsonpify(ret)
        else:
            return jsonpify(MANIFEST)

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
