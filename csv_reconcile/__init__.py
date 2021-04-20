from flask import Flask, request, jsonify
from flask_cors import cross_origin
from .score import processQueryBatch
from .extend import getCSVCols, processDataExtensionBatch
from . import initdb
from . import default_settings
from . import scorer
import json
import os.path
from contextlib import contextmanager
import time
import click

try:
    from importlib import metadata
except:
    import importlib_metadata as metadata

__version__ = '0.2.1'
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


# Default manifest.  Can be overriden/updated in configuration
MANIFEST = {
    "versions": ["0.1"],
    "name": "CSV Reconcile",
    "identifierSpace": "http://localhost/csv_reconcile/ids",
    "schemaSpace": "http://localhost/csv_reconcile/schema",
    "extend": {
        "propose_properties": {
            "service_url": "http://localhost:5000",
            "service_path": "/properties"
        }
    }
}


def create_app(setup=None, config=None, instance_path=None):
    app = Flask("csv-reconcile", instance_path=instance_path)
    # Could make dbname configurable
    # possibly better to roll THRESHOLD and LIMIT into one config called LIMITS
    app.config.from_object(default_settings)
    if config:
        app.config.from_pyfile(config)

    app.config.from_mapping(**setup)
    scoreOptions = app.config['SCOREOPTIONS']
    scorer.processScoreOptions(scoreOptions)

    if 'MANIFEST' in app.config:
        MANIFEST.update(app.config['MANIFEST'])

    loglevel = app.config['LOGLEVEL']
    if loglevel:
        app.logger.setLevel(loglevel)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.before_request
    def before():
        app.logger.debug(request.method)
        app.logger.debug(request.headers)

    @app.after_request
    def after(response):
        app.logger.debug(response.headers)
        return response

    @app.route('/reconcile', methods=['POST', 'GET'])
    @cross_origin()
    def acceptQuery():
        threshold = app.config.get('THRESHOLD', None)
        limit = app.config.get('LIMIT', None)
        scoreOptions = app.config['SCOREOPTIONS']
        queries = request.form.get('queries')
        extend = request.form.get('extend')
        if queries:
            queryBatch = json.loads(queries)

            app.logger.info(queryBatch)
            with Timer():
                ret = processQueryBatch(queryBatch,
                                        limit=limit,
                                        threshold=threshold,
                                        **scoreOptions)
            app.logger.info(ret)
            return ret
        elif extend:
            extendBatch = json.loads(extend)

            app.logger.info(extendBatch)
            with Timer():
                ret = processDataExtensionBatch(extendBatch)
            app.logger.info(ret)
            return ret
        else:
            return MANIFEST

    # FIX FIX FIX...  Not needed in OpenRefine 3.5
    # [[https://github.com/OpenRefine/OpenRefine/issues/3672]]
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

    @app.route('/properties', methods=['POST', 'GET'])
    @cross_origin()
    def acceptPropertyRequest():
        # query string arg
        propType = request.args.get('type')

        # Type irrelevant, return all columns
        if propType != None:
            cols = getCSVCols()
            ret = dict(properties=[{
                'id': colname,
                'name': name
            } for name, colname in cols])
            return jsonpify(ret)

        # unprocessible request

    return app


def pickScorer(plugin):
    eps = metadata.entry_points().get('csv_reconcile.scorers', [])
    if len(eps) == 0:
        raise RuntimeError("Please install a \"csv_reconcile.scorers\" plugin")
    elif plugin:
        for ep in eps:
            if ep.name == plugin:
                return ep
        else:
            raise RuntimeError(
                "Please install %s \"csv_reconcile.scorers\" plugin" %
                (plugin,))
    elif len(eps) == 1:
        return next(iter(eps))

    # print out options
    print(
        "There are several scorers available.  Please choose one of the following with the --scorer option."
    )
    for ep in eps:
        print("  %s" % (ep.name,))

    return None


@click.command()
@click.option('--config', help='config file')
@click.option('--scorer', 'scorerOption', help='scoring plugin to use')
@click.option('--init-db', is_flag=True, help='initialize the db')
@click.argument('csvfile')
@click.argument('idcol')
@click.argument('namecol')
def main(config, scorerOption, init_db, csvfile, idcol, namecol):
    ep = pickScorer(scorerOption)
    if ep:
        ep.load()
    else:
        return

    eps = metadata.entry_points()['csv_reconcile.scorers']
    if len(eps) == 0:
        raise RuntimeError("Please install a \"csv_reconcile.scorers\" plugin")
    elif scorerOption:
        for ep in eps:
            if ep.name == scorerOption:
                ep.load()
                break
        else:
            raise RuntimeError(
                "Please install %s \"csv_reconcile.scorers\" plugin" %
                (scorerOption,))
    elif len(eps) == 1:
        ep = next(iter(eps))
        ep.load()
    else:
        # prompt for options and quit
        pass

    app = create_app(dict(CSVFILE=csvfile, CSVCOLS=(idcol, namecol)), config)
    if init_db:
        with app.app_context():
            initdb.init_db()
            click.echo('Initialized the database.')

    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run()
