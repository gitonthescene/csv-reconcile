import pytest
from csv_reconcile import __version__
import json
from urllib.parse import urlencode


def test_version():
    assert __version__ == '0.1.2'


def test_manifest(basicClient):
    response = basicClient.get('/reconcile')

    assert response.status_code == 200

    manifest = json.loads(response.data)
    expectedKeys = set(
        'versions name identifierSpace schemaSpace extend'.split())

    assert set(manifest.keys()).intersection(expectedKeys) == expectedKeys


def test_query_basics(basicClient, formContentHeader):
    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    response = basicClient.post('/reconcile',
                                data=urlencode([('queries', queryjson)]),
                                headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert query.keys() == matchBatch.keys()

    somekey = next(iter(matchBatch))

    assert 'result' in matchBatch[somekey]
    assert type(matchBatch[somekey]['result']) == list


def test_data_extension_basics(basicClient, setup, header, typicalrow,
                               formContentHeader):

    # Type is ignored in this service
    dummyType = ''
    idcol, namecol = setup['CSVCOLS']
    ididx = header.index(idcol)

    response = basicClient.get('/properties?type=%s' % (dummyType,))

    assert response.status_code == 200

    cols = json.loads(response.data)

    assert 'properties' in cols
    assert type(cols['properties']) == list  # [ {id:..., name:...}, ... ]

    # Every thing but id and name col available for extension
    availableCols = {}
    for itm in cols['properties']:

        # internal and external column name
        assert set(itm.keys()) == set(('id', 'name'))

        availableCols[itm['id']] = itm['name']

    assert set(availableCols) == set(header).difference((idcol, namecol))

    colid = typicalrow[ididx]
    req = {'ids': [colid], 'properties': cols['properties']}
    reqjson = json.dumps(req)
    response = basicClient.post('/reconcile',
                                data=urlencode([('extend', reqjson)]),
                                headers=formContentHeader)

    assert response.status_code == 200

    extenddata = json.loads(response.data)

    assert 'meta' in extenddata
    assert 'rows' in extenddata
    assert colid in extenddata['rows']

    row = extenddata['rows'][colid]
    for colextra, colextra_dbnm in availableCols.items():
        exidx = header.index(colextra)

        assert colextra_dbnm in row

        for choice in row[colextra_dbnm]:
            assert 'str' in choice
            assert choice['str'] == typicalrow[exidx]


@pytest.fixture
def lclient(client, setup, tmp_path):
    filecontents = '''
LIMIT=2
THRESHOLD=-1.0
import logging
LOGLEVEL=logging.DEBUG'''
    p = tmp_path / "config"
    p.write_text(filecontents)
    return client(setup, p)


def test_reconcile_limit(lclient, formContentHeader):
    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    response = lclient.post('/reconcile',
                            data=urlencode([('queries', queryjson)]),
                            headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert len(matchBatch['q0']['result']) == 2
    response = lclient.post('/reconcile',
                            data=urlencode([('queries', queryjson)]),
                            headers=formContentHeader)

    # Override config limit in query with larger number
    query = {'q0': {'query': 'first', 'limit': 3}}
    queryjson = json.dumps(query)
    response = lclient.post('/reconcile',
                            data=urlencode([('queries', queryjson)]),
                            headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    # Matches override
    assert len(matchBatch['q0']['result']) == 3

    # Override config limit in query with smaller number
    query = {'q0': {'query': 'first', 'limit': 1}}
    queryjson = json.dumps(query)
    response = lclient.post('/reconcile',
                            data=urlencode([('queries', queryjson)]),
                            headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    # Matches override
    assert len(matchBatch['q0']['result']) == 1


def test_reconcile_automatch(basicClient, formContentHeader):
    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    response = basicClient.post('/reconcile',
                                data=urlencode([('queries', queryjson)]),
                                headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)
    result = matchBatch['q0']['result']

    # Only one with 100% match automatches
    cnt = 0
    for itm in result:
        if itm['name'] == 'first':
            cnt += 1
            assert itm['match'] == True
            assert itm['score'] == 100.0
        else:
            assert itm['match'] == False

    assert cnt == 1

    # None with 100% match does not automatch
    query = {'q0': {'query': 'fir'}}
    queryjson = json.dumps(query)
    response = basicClient.post('/reconcile',
                                data=urlencode([('queries', queryjson)]),
                                headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)
    result = matchBatch['q0']['result']

    assert all(
        itm['match'] == False and itm['score'] != 100.0 for itm in result)

    # Only one result automatches, even if not 100%
    query = {'q0': {'query': 'fir', 'limit': 1}}
    queryjson = json.dumps(query)
    response = basicClient.post('/reconcile',
                                data=urlencode([('queries', queryjson)]),
                                headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)
    result = matchBatch['q0']['result']
    assert len(result) == 1
    assert result[0]['score'] != 100.0 and result[0]['match'] == True
