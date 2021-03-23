from csv_reconcile import __version__
import json
from urllib.parse import urlencode


def test_version():
    assert __version__ == '0.1.1'


def test_manifest(client):
    response = client.get('/reconcile')

    assert response.status_code == 200

    manifest = json.loads(response.data)
    expectedKeys = set(
        'versions name identifierSpace schemaSpace extend'.split())

    assert set(manifest.keys()).intersection(expectedKeys) == expectedKeys


def test_query_basics(client, formContentHeader):
    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert query.keys() == matchBatch.keys()

    somekey = next(iter(matchBatch))

    assert 'result' in matchBatch[somekey]
    assert type(matchBatch[somekey]['result']) == list


def test_data_extension_basics(client, setup, header, typicalrow,
                               formContentHeader):

    # Type is ignored in this service
    dummyType = ''
    idcol, namecol = setup['CSVCOLS']
    ididx = header.index(idcol)

    response = client.get('/properties?type=%s' % (dummyType,))

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
    response = client.post('/reconcile',
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
