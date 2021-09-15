import os
from tests import config


def test_config():
    assert os.path.exists(config.UPLOAD_DIR)
    assert config.SQLALCHEMY_DATABASE_URI == os.environ["SQLALCHEMY_DATABASE_URI"]
    assert config.UPLOAD_DIR == os.environ["UPLOAD_DIR"]
