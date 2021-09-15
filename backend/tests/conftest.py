import os
import shutil

import pytest
from dramatiq import Worker
from sqlalchemy_utils import drop_database, create_database, database_exists

from api import engine, scripts
from api.pipelining._tasks import broker

from tests import client, testing_session, models, TEST_USER, utils, config


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    assert "test" in str(url := engine.url)

    if os.path.exists(config.UPLOAD_DIR):
        shutil.rmtree(config.UPLOAD_DIR)

    if database_exists(url):
        drop_database(url)

    create_database(engine.url)
    models.Base.metadata.create_all(bind=engine)
    scripts.run_startup_scripts()

    utils.create_local_user(**TEST_USER.dict())

    yield


@pytest.fixture
def db():
    with testing_session() as db:
        yield db


@pytest.fixture()
def stub_broker():
    broker.flush_all()
    return broker


@pytest.fixture()
def stub_worker():
    worker = Worker(broker, worker_timeout=100)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture(scope="module")
def authorization_header():
    response = client.post(
        "/auth/token",
        data={"username": TEST_USER.username, "password": TEST_USER.password},
    )
    assert response.status_code == 200

    return {"Authorization": f'Bearer {response.json()["access_token"]}'}
