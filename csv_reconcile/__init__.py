import json
import os.path
from pathlib import Path
import sys
import time
import shutil
from contextlib import contextmanager

import click
from flask import abort, Flask, jsonify, request
from flask_cors import cross_origin
from markupsafe import escape

from . import default_settings, initdb, scorer
from .db import get_db, getCSVCols
from .extend import processDataExtensionBatch
from .preview import getEntity
from .score import processQueryBatch

try:
    import importlib_metadata as metadata
except:
    from importlib import metadata

__version__ = '0.3.0'
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


def create_app(config=None, instance_path=None, scorerOption=None):
    app = Flask("csv-reconcile", instance_path=instance_path)

    instance_path = Path(app.instance_path)

    try:
        os.makedirs(instance_path)
    except OSError:
        pass

    scorerfile = instance_path / 'scorer.txt'

    # clean up old files if they exist
    # "" indicates called from doinit()
    if scorerOption == "" and scorerfile.is_file():
        scorerfile.unlink()
    elif scorerOption:
        with open(scorerfile, 'w') as f:
            f.write(scorerOption)

    scorerOption = None
    if scorerfile.is_file():
        with open(scorerfile) as f:
            scorerOption = f.read()

    if pickScorer(scorerOption) is None:
        return None

    # possibly better to roll THRESHOLD and LIMIT into one config called LIMITS
    app.config.from_object(default_settings)

    cfgfile = instance_path / "reconcile.config"

    # clean up old configs if they exist
    # "" indicates called from doinit()
    if config == "" and cfgfile.is_file():
        cfgfile.unlink()
    elif config:
        shutil.copyfile( config, cfgfile )

    if cfgfile.is_file():
        app.config.from_pyfile(cfgfile)

    scoreOptions = app.config['SCOREOPTIONS']
    scorer.processScoreOptions(scoreOptions)

    if 'MANIFEST' in app.config:
        MANIFEST.update(app.config['MANIFEST'])

    loglevel = app.config['LOGLEVEL']
    if loglevel:
        app.logger.setLevel(loglevel)

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
            db = get_db()

            queryBatch = json.loads(queries)

            app.logger.info(queryBatch)
            with Timer():
                ret = processQueryBatch(db,
                                        queryBatch,
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
            } for colname, name in cols])
            return jsonpify(ret)

        # unprocessible request

    @app.route('/preview/<entity_id>')
    @cross_origin()
    def preview_service(entity_id=None):
        if not entity_id:
            abort(404)
        entity = getEntity(entity_id)
        if not entity:
            abort(404)
        entity_html = "".join([f"<dt>{escape(key)}</dt><dd>{escape(val)}</dd>"
                               for key, val in entity.items()])
        return f"""<!DOCTYPE html>
<html>
    <head>
        <meta charset='utf-8'>
        <title>Preview for {escape(entity_id)}</title>
        <style type='text/css'>
          h1 {{font-size: 115%; }}
          dl {{display: flex; flex-flow: row wrap;}}
          dt {{flex-basis: 20%; padding: 2px 4px;
               text-align: right; font-weight: bold;}}
          dt::after {{content: ':';}}
          dd {{flex-basis: 70%; flex-grow: 1;
               margin: 0; padding: 2px 4px;}}
        </style>
    </head>
    <body>
        <dl>{entity_html}</dl>
    </body>
</html>"""

    return app


def pickScorer(plugin):
    eps = metadata.entry_points().select(group='csv_reconcile.scorers')
    entrypoint = None
    if len(eps) == 0:
        raise RuntimeError("Please install a \"csv_reconcile.scorers\" plugin")
    elif plugin:
        for ep in eps:
            if ep.name == plugin:
                entrypoint = ep
                break
        else:
            raise RuntimeError(
                "Please install %s \"csv_reconcile.scorers\" plugin" %
                (plugin,))
    elif len(eps) == 1:
        entrypoint = next(iter(eps))

    if entrypoint is None:
        # print out options
        print(
            "There are several scorers available.  Please choose one of the following with the --scorer option."
        )
        for ep in eps:
            print("  %s" % (ep.name,))
        return None

    entrypoint.load()
    return entrypoint


@click.group()
def cli():
    pass


def doinit(config, scorerOption, csvfile, idcol, namecol):

    app = create_app(config or "", scorerOption=scorerOption or "")
    if app is None:
        return

    with app.app_context():
        initdb.init_db_with_context(csvfile, idcol, namecol)
        click.echo('Initialized the database.')
    return app


@cli.command()
@click.option('--config', help='config file')
@click.option('--scorer', 'scorerOption', help='scoring plugin to use')
@click.argument('csvfile')
@click.argument('idcol')
@click.argument('namecol')
def init(config, scorerOption, csvfile, idcol, namecol):
    return doinit(config, scorerOption, csvfile, idcol, namecol)

@cli.command()
@click.option('--config', help='config file')
@click.option('--scorer', 'scorerOption', help='scoring plugin to use')
@click.option('--init-db', is_flag=True, help='initialize the db')
@click.argument('csvfile')
@click.argument('idcol')
@click.argument('namecol')
def run(config, scorerOption, init_db, csvfile, idcol, namecol):
    print('''
#########################################################
##         WARNING: The interface is deprecated        ##
#########################################################

Please run init once to initialize the database and serve to run the server.
See --help for details.
''')

    app = None
    if init_db:
        app = doinit(config, scorerOption, csvfile, idcol, namecol)

    app = app or create_app(config)
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(debug=False)


@cli.command()
def serve():

    # Config should have been copied during the init phase
    app = create_app()
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(debug=False)


def main():
    nonopts = [a for a in sys.argv if not a.startswith('--')]

    if len(nonopts) > 1 and nonopts[1] not in 'run init serve':
        print('''
#########################################################
##     WARNING: The interface has changed slightly.    ##
#########################################################
Please use one of the subcommands. See --help for details.

''')
    return cli()
