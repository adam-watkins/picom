import os
import pathlib
import shutil

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DIR = pathlib.Path(__file__).parent
UPLOAD_DIR = TEST_DIR / ".test_uploads"

os.environ["UNIT_TESTING"] = "True"
os.environ[
    "SQLALCHEMY_DATABASE_URI"
] = f"sqlite:///{str(TEST_DIR)}/.test.db?check_same_thread=False"
os.environ["UPLOAD_DIR"] = str(UPLOAD_DIR)
os.environ["UPLOAD_VOLUME_ABSPATH"] = str(UPLOAD_DIR)
os.environ["SCP_PORT"] = "11122"
os.environ["LDAP_AUTH_ENABLED"] = "False"

from api import app, models, config, schemas
from api.database import worker_session as testing_session

client = TestClient(app)

TEST_USER = schemas.user.UserLocalCreate(
    username="test_user", name="Test User", password="PassWord"
)

from . import _mark as mark
