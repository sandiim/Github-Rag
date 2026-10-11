from app.persistence.session import create_session_factory


def test_session_factory_connects_to_the_supplied_database_url() -> None:
    session_factory = create_session_factory("sqlite://")

    with session_factory() as session:
        assert session.connection().dialect.name == "sqlite"
