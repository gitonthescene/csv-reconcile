from nox_poetry import session, SDIST

args = lambda s: s.split()


@session(python=['3.7', '3.8', '3.9'])
def test_main(session):
    session.poetry.installroot(distribution_format=SDIST)
    session.install('pytest')
    session.run(*args('pytest -v tests/main'))


@session(python=['3.7', '3.8', '3.9'])
def test_geo(session):
    session.poetry.installroot(distribution_format=SDIST)
    session.install('csv-reconcile-geo')
    session.install('pytest')
    session.run(*args('pytest -v tests/plugins/geo'))
