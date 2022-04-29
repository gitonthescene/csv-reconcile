import pytest

from csv_reconcile import __version__, scorer
from csv_reconcile.db import getCSVCols

import json
from urllib.parse import urlencode


def test_version():
    assert __version__ == '0.3.1'


def test_manifest(basicClient):
    response = basicClient().get('/reconcile')

    assert response.status_code == 200

    manifest = json.loads(response.data)
    expectedKeys = set(
        'versions name identifierSpace schemaSpace extend'.split())

    assert set(manifest.keys()).intersection(expectedKeys) == expectedKeys


def test_query_basics(basicClient, formContentHeader):
    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    response = basicClient().post('/reconcile',
                                  data=urlencode([('queries', queryjson)]),
                                  headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert query.keys() == matchBatch.keys()

    assert 'result' in matchBatch['q0']
    assert type(matchBatch['q0']['result']) == list


def test_data_extension_basics(basicClient, setup, header, typicalrow,
                               formContentHeader):

    client = basicClient()
    # Type is ignored in this service
    dummyType = ''
    _, idcol, namecol = setup
    ididx = header.index(idcol)

    response = client.get('/properties?type=%s' % (dummyType,))

    assert response.status_code == 200

    cols = json.loads(response.data)

    assert 'properties' in cols
    assert type(cols['properties']) == list  # [ {id:..., name:...}, ... ]

    availableCols = dict()
    for itm in cols['properties']:
        assert set(itm.keys()) == set(('id', 'name'))

        availableCols[itm['name']] = itm['id']

    assert set(availableCols) == set(header)

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
    for colextra, colid in availableCols.items():
        exidx = header.index(colextra)

        assert colid in row

        for choice in row[colid]:
            assert 'str' in choice
            assert choice['str'] == typicalrow[exidx]


def test_preview_service(basicClient, setup, header, typicalrow):
    client = basicClient()

    # no id
    response = client.get(f"/preview/")
    assert response.status_code == 404

    # unavailable id
    response = client.get(f"/preview/unavailable")
    assert response.status_code == 404

    # available id
    id_idx = header.index(setup[1])
    response = client.get(f"/preview/{typicalrow[id_idx]}")
    assert response.status_code == 200

    html_response = response.data.decode("utf-8")
    print(html_response)
    assert f"<title>Preview for {typicalrow[id_idx]}</title>" in html_response
    for key, value in zip(header, typicalrow):
        assert f"<dt>{key}</dt><dd>{value}</dd>" in html_response


@pytest.fixture
def limitConfig(mkConfig):
    contents = '''
LIMIT=2
THRESHOLD=-1.0
import logging
LOGLEVEL=logging.DEBUG
'''
    return mkConfig(contents)


def test_reconcile_limit(basicClient, formContentHeader, limitConfig):
    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    client = basicClient(limitConfig)
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert len(matchBatch['q0']['result']) == 2
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)

    # Override config limit in query with larger number
    query = {'q0': {'query': 'first', 'limit': 3}}
    queryjson = json.dumps(query)
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    # Matches override
    assert len(matchBatch['q0']['result']) == 3

    # Override config limit in query with smaller number
    query = {'q0': {'query': 'first', 'limit': 1}}
    queryjson = json.dumps(query)
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    # Matches override
    assert len(matchBatch['q0']['result']) == 1


def test_reconcile_automatch(basicClient, formContentHeader):
    client = basicClient()

    query = {'q0': {'query': 'first'}}
    queryjson = json.dumps(query)
    response = client.post('/reconcile',
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
    response = client.post('/reconcile',
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
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)
    result = matchBatch['q0']['result']
    assert len(result) == 1
    assert result[0]['score'] != 100.0 and result[0]['match'] == True


def test_plugin(mockPlugin, basicClient, csvcontents, formContentHeader):
    # Since used in closure pass in "by reference"
    p, gn, nw, sm, v = list(range(5))
    called = [0] * 5

    @scorer.register
    def processScoreOptions(options):
        called[p] += 1

    @scorer.register
    def getNormalizedFields():
        # one normalized field
        called[gn] += 1
        return ('dummy',)

    @scorer.register
    def normalizeWord(word, **scoreOptions):
        # everything normalizes to COW thus everything matches
        called[nw] += 1
        return ("COW",)

    @scorer.register
    def scoreMatch(left, right):
        # Count the number of letters in common
        called[sm] += 1
        left, right = left[0], right[0]
        return len(set(left).intersection(right)) / len(left) * 100.0

    @scorer.register
    def valid(normalizedFields):
        called[v] += 1
        return True

    client = basicClient()

    # processScoreOptions, getNormalizedFields, and normalizeWord all called during setup
    # scoreMatch and valid not yet called
    assert all(called[itm] > 0 for itm in (p, gn, nw))
    assert called[sm:] == [0, 0]

    # total number of rows minus 1 for the header row
    nRows = len(csvcontents.splitlines()) - 1

    query = {'q0': {'query': 'mxyzptlk'}}
    queryjson = json.dumps(query)
    response = client.post('/reconcile',
                           data=urlencode([('queries', queryjson)]),
                           headers=formContentHeader)
    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert len(matchBatch['q0']['result']) == nRows
    assert all(called[itm] > 0 for itm in (p, gn, nw, sm, v))

    # processScoreOptions still called once, getNormalizedFields only called twice
    assert called[:2] == [1, 2]

def test_csv_sniffer_overrides(app, ambiguous_setup, ambiguous_csvcontents, config, mkConfig):

    topline = ambiguous_csvcontents.splitlines()[0]
    items = lambda sep: [ h.strip() for h in topline.split(sep)]

    # First guess is that the , is a separator
    SEP = ','
    chk = app(ambiguous_setup(items(SEP)[:2]), config)
    with chk.app_context():
        headernms = [name for _,name in getCSVCols()]
        assert headernms == items(SEP)

    # Now parse with override
    SEP = ' '
    cfg = mkConfig('CSVKWARGS = {"delimiter": " "}')
    chk = app(ambiguous_setup(items(SEP)[:2]), cfg)
    with chk.app_context():
        headernms = [name for _,name in getCSVCols()]
        assert headernms == items(SEP)
