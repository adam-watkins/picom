from time import sleep
import os
import shutil
from pathlib import Path

import pytest
from pynetdicom import AE, StoragePresentationContexts, debug_logger
from pynetdicom.sop_class import VerificationSOPClass

from api.dicom.scp import SCP
from tests import config

TMP_FOLDER = Path(__file__).parent / "tmp"
MOCK_DATA_DIR = Path(__file__).parent / "mock_data"


@pytest.fixture(scope="module", autouse="True")
def scp_server():
    scp_server = SCP(
        ae_title=config.SCP_AE_TITLE, host=config.SCP_HOST, port=config.SCP_PORT
    )
    scp_server.start_server(blocking=False)

    yield

    scp_server.stop_server()


@pytest.fixture(scope="module")
def mock_path():
    assert MOCK_DATA_DIR.exists()
    yield MOCK_DATA_DIR


@pytest.fixture()
def tmp_folder():
    if TMP_FOLDER.exists():
        shutil.rmtree(TMP_FOLDER)

    TMP_FOLDER.mkdir(parents=True, exist_ok=True)
    yield Path(TMP_FOLDER)
