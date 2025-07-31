"""Configuration for nox matrix testing."""
from nox_poetry import session, SDIST


def args(s):
    """Split args into an array."""
    return s.split()


@session(python=['3.10', '3.11', '3.12', '3.13'])
def test_main(session):
    """Test with main scorer."""
    session.poetry.installroot(distribution_format=SDIST)
    session.install('pytest')
    session.run(*args('pytest -v tests/main'))


@session(python=['3.10', '3.11', '3.12', '3.13'])
def test_geo(session):
    """Test with geo scorer."""
    session.poetry.installroot(distribution_format=SDIST)
    session.install('csv-reconcile-geo')
    session.install('pytest')
    session.run(*args('pytest -v tests/plugins/geo'))
