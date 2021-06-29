import pytest
import json
from urllib.parse import urlencode
from pprint import pprint as pp
from geopy import distance


@pytest.fixture
def toResolve():
    data = '''
city	cityLabel	coords
Q1342	Pittsburgh	Point(-80.0 40.441666666)
Q5083	Seattle	Point(-122.33207 47.60621)
Q16559	Austin	Point(-97.733333333 30.3)
Q43196	Cincinnati	Point(-84.5 39.133333333)
'''.strip()
    return {
        cityNm: coords
        for cityId, cityNm, coords in (l.split('\t') for l in data.splitlines())
    }


@pytest.fixture
def baseDataLkupNm(csvcontents):
    return {
        cityId: cityNm for cityId, cityNm, _ in (
            l.split('\t') for l in csvcontents.splitlines())
    }


@pytest.fixture
def baseDataLkupCoord(csvcontents):
    return {
        cityNm: coords for _, cityNm, coords in (
            l.split('\t') for l in csvcontents.splitlines())
    }


def test_query(basicClient, config, formContentHeader, toResolve,
               baseDataLkupNm):

    ccoords = toResolve['Seattle']

    query = {'q0': {'query': ccoords}}
    queryjson = json.dumps(query)
    response = basicClient(config).post('/reconcile',
                                        data=urlencode([('queries', queryjson)
                                                       ]),
                                        headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert query.keys() == matchBatch.keys()

    results = matchBatch['q0']['result']
    best = max(results, key=lambda x: x['score'])

    assert baseDataLkupNm[best['id']] == 'Los Angeles'


@pytest.fixture
def scaleConfig(mkConfig, baseDataLkupCoord, toResolve):

    # convert wkt format to tuple of floats (lat, lon)
    mkpt = lambda wkt: tuple(float(x) for x in wkt[6:-1].split()[1::-1])

    chicago = baseDataLkupCoord['Chicago']
    pittsburgh = toResolve['Pittsburgh']

    dist = distance.geodesic(mkpt(chicago), mkpt(pittsburgh)).km

    contents = f'''
THRESHOLD=0.0
import logging
LOGLEVEL=logging.DEBUG
SCOREOPTIONS = {{
  "SCALE": {dist}
}}
'''
    return mkConfig(contents)


def test_scale(basicClient, scaleConfig, formContentHeader, toResolve,
               baseDataLkupNm):

    pittsburgh = toResolve['Pittsburgh']

    query = {'q0': {'query': pittsburgh}}
    queryjson = json.dumps(query)
    response = basicClient(scaleConfig).post('/reconcile',
                                             data=urlencode([('queries',
                                                              queryjson)]),
                                             headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert query.keys() == matchBatch.keys()

    results = matchBatch['q0']['result']

    score = {baseDataLkupNm[r['id']]: r['score'] for r in results}

    assert score['Chicago'] == 50  # Right at scale
    assert score['New York City'] > 50  # closer
    assert score['Miami'] < 50  # further


@pytest.fixture
def rangeConfig(mkConfig, baseDataLkupCoord, toResolve):

    contents = f'''
THRESHOLD=0.0
import logging
LOGLEVEL=logging.DEBUG
SCOREOPTIONS = {{
  "COORDRANGE": 10.0
}}
'''
    return mkConfig(contents)


def test_range(basicClient, rangeConfig, formContentHeader, toResolve,
               baseDataLkupNm):

    pittsburgh = toResolve['Pittsburgh']

    query = {'q0': {'query': pittsburgh}}
    queryjson = json.dumps(query)
    response = basicClient(rangeConfig).post('/reconcile',
                                             data=urlencode([('queries',
                                                              queryjson)]),
                                             headers=formContentHeader)

    assert response.status_code == 200

    matchBatch = json.loads(response.data)

    assert query.keys() == matchBatch.keys()

    results = matchBatch['q0']['result']

    # Only NYC and Chicago have longitude and latitude within 10 points
    assert len(results) == 2

    score = {baseDataLkupNm[r['id']]: r['score'] for r in results}

    assert 'Chicago' in score
    assert 'New York City' in score
