from nox_poetry import session, SDIST


@session(python=['3.7', '3.8', '3.8'])
def test(session):
    session.poetry.installroot(distribution_format=SDIST)
    session.install('pytest')
    session.run('pytest')
