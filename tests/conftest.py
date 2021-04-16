import pytest
from csv_reconcile import create_app, initdb, scorer
import types
try:
    from importlib import metadata
except:
    import importlib_metadata as metadata


@pytest.fixture
def plugins():
    '''csv_reconcile.scorers plugins'''
    eps = metadata.entry_points()['csv_reconcile.scorers']
    return {ep.name: ep for ep in eps}


@pytest.fixture
def csvcontents():
    '''contents for mock csv file'''
    # Column names are normalized for database use
    # id column need not be first nor name name second
    return '''
name@hdr	id hdr	extra!hdr
first	1	stuff
second	2	junk
third	3	and so on
'''.strip()


@pytest.fixture
def formContentHeader():
    '''header for form data for client'''
    return {'content-type': 'application/x-www-form-urlencoded'}


@pytest.fixture
def header(csvcontents):
    '''header of mock csvfile'''
    return csvcontents.splitlines()[0].split('\t')


@pytest.fixture
def typicalrow(csvcontents):
    '''typical row of mock csvfile'''
    return csvcontents.splitlines()[1].split('\t')


@pytest.fixture
def setup(tmp_path, csvcontents, header, typicalrow):
    '''mock csv file with id and name columns indicated'''

    p = tmp_path / "csvfile"
    p.write_text(csvcontents)
    return dict(CSVFILE=p, CSVCOLS=tuple(reversed(header[:2])))


@pytest.fixture
def config(tmp_path):
    '''mock server config'''
    filecontents = '''
THRESHOLD=0.0
import logging
LOGLEVEL=logging.DEBUG'''
    p = tmp_path / "config"
    p.write_text(filecontents)

    return p


@pytest.fixture
def mockPlugin():
    '''save/restore original plugin API'''
    saveOrig = {
        nm: vl
        for nm, vl in scorer.__dict__.items()
        if type(vl) == types.FunctionType
    }
    yield saveOrig
    for nm, fn in saveOrig.items():
        setattr(scorer, nm, fn)


@pytest.fixture
def app(plugins, tmp_path):
    '''flask app'''
    # Apply the dice plugin
    plugins['dice'].load()

    def getApp(setup, config):
        app = create_app(setup, config, instance_path=tmp_path / "instance")
        with app.app_context():
            initdb.init_db()

        return app

    return getApp


@pytest.fixture
def client(app):
    '''http client'''

    def getClient(setup, config):
        return app(setup, config).test_client()

    return getClient


@pytest.fixture
def basicClient(client, setup, config):
    return client(setup, config)
