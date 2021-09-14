import os
import pytest
from api.models.pipeline import Pipeline, PipelineRun
from tests import config

from api.services import DicomIngestService

from tests.test_models.test_pipelines import insert_pipeline


def test_ingest_with_bad_ae_title(mock_images_folder, db):
    with pytest.raises(ValueError):
        with DicomIngestService(
            folder=mock_images_folder,
            called_aet="BAD_AET",
            calling_aet="Test",
            calling_host="localhost",
        ) as ingest:
            ingest.execute()


def test_ingest_folder_to_bad_pipeline(mock_images_folder, db):
    with pytest.raises(AssertionError):
        with DicomIngestService(
            folder=mock_images_folder,
            called_aet=config.PIPELINE_AE_PREFIX + "non-existant-user",
            calling_aet="Test",
            calling_host="localhost",
        ) as ingest:
            ingest.execute()
