"""SQLAlchemy engine and session-factory helpers."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create sessions bound to one database URL."""

    engine: Engine = create_engine(database_url)
    return sessionmaker(bind=engine)
