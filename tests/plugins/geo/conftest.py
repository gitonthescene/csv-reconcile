import pytest


@pytest.fixture
def csvcontents():
    return '''
city	cityLabel	coords
Q60	New York City	Point(-73.94 40.67)
Q65	Los Angeles	Point(-118.24368 34.05223)
Q1297	Chicago	Point(-87.627777777 41.881944444)
Q8652	Miami	Point(-80.216666666 25.783333333)
'''.strip()


@pytest.fixture
def idnm(header):
    '''id and name cols from the header'''
    return (header[0], header[2])


@pytest.fixture
def basicClient(client, setup):

    def getClient(config):
        return client(setup, config, plugin='geo')

    return getClient
