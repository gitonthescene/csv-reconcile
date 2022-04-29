import pytest
from csv_reconcile import create_app, initdb, scorer
import types
try:
    import importlib_metadata as metadata
except:
    from importlib import metadata


@pytest.fixture
def plugins():
    '''csv_reconcile.scorers plugins'''
    eps = metadata.entry_points().select(group='csv_reconcile.scorers')
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
def ambiguous_csvcontents():
    '''Try to throw off csv.Sniffer() to test overrides'''
    return '''
These, my friends, are the columns
However, above all, columns matter most
'''.strip()

@pytest.fixture
def sniffer_throwing_csvcontents():
    '''Try to throw off csv.Sniffer() to test overrides'''
    return '''
a,b,c\n1,2
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
def idnm(header):
    '''id and name cols from the header'''
    return (header[1], header[0])


@pytest.fixture
def typicalrow(csvcontents):
    '''typical row of mock csvfile'''
    return csvcontents.splitlines()[1].split('\t')


@pytest.fixture
def setup(tmp_path, csvcontents, idnm):
    '''mock csv file with id and name columns indicated'''

    p = tmp_path / "csvfile"
    p.write_text(csvcontents)
    return (p, *idnm)

@pytest.fixture
def ambiguous_setup(tmp_path, ambiguous_csvcontents):
    '''mock csv file with id and name columns indicated'''

    def getSetup(idnm):
        p = tmp_path / "amb_csvfile"
        p.write_text(ambiguous_csvcontents)
        return (p, *idnm)

    return getSetup

@pytest.fixture
def sniffer_throwing_setup(tmp_path, sniffer_throwing_csvcontents):
    '''mock csv file with id and name columns indicated'''

    def getSetup(idnm):
        p = tmp_path / "snfthrw_csvfile"
        p.write_text(sniffer_throwing_csvcontents)
        return (p, *idnm)

    return getSetup

@pytest.fixture
def cfgContents():
    return '''
THRESHOLD=0.0
import logging
LOGLEVEL=logging.DEBUG'''


@pytest.fixture
def mkConfig(tmp_path):
    '''make server config'''

    def fn(cfgContents):
        p = tmp_path / "config"
        p.write_text(cfgContents)

        return p

    return fn


@pytest.fixture
def config(mkConfig, cfgContents):
    '''mock server config'''
    return mkConfig(cfgContents)


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

    def getApp(setup, config, plugin='dice'):
        app = create_app(config, instance_path=tmp_path / "instance", scorerOption=plugin)
        with app.app_context():
            initdb.init_db_with_context(*setup)

        return app

    return getApp


@pytest.fixture
def client(app):
    '''http client'''

    def getClient(setup, config, plugin='dice'):
        return app(setup, config, plugin=plugin).test_client()

    return getClient


@pytest.fixture
def basicClient(client, setup, config):

    def getClient(config=config):
        return client(setup, config, plugin='dice')

    return getClient
