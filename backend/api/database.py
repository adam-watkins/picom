from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from inflection import underscore

from api import config

engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def worker_session():
    """
    This session is meant to be used outside of fastapi. A session can be obtained with:
        with worker_session() as db:
            db.query(model).all()
            ...
    """

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def session():
    """This session is meant to be used inside of fastapi with Depends(session)"""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
