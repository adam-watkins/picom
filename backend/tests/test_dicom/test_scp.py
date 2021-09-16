import os
from time import sleep

from pydicom import dcmread
from pynetdicom import AE, StoragePresentationContexts, debug_logger
from pynetdicom.sop_class import VerificationSOPClass

from api.dicom.scp import SCP
from api.models.dicom import DicomNode, DicomSeries
from api.models.pipeline import Pipeline, PipelineRun
from api.schemas.dicom import DicomNode as DicomNodeSchema
from api.queries.internal import get_return_to_sender

from tests import client, config, models, mark, utils

import logging
from tests.test_models.test_containers import (
    create_and_test_container,
    delete_and_test_container,
)

from tests.test_models.test_pipelines import insert_pipeline, LinearPipelineFactory
from tests.test_pipelining.test_build import build_container_foreground

logging.basicConfig(level=logging.DEBUG)


def join(broker, worker):
    broker.join("default", fail_fast=True)
    worker.join()


def test_scp_class(ae_title: str = "TEST_AE_TITLE", port: int = 11010) -> SCP:
    scp = SCP(ae_title=ae_title, port=port)

    assert scp.ae_title == ae_title
    assert scp.port == port

    return scp


def test_scp_sever_startup_and_shutdown():
    scp = test_scp_class()

    scp.start_server()
    scp.stop_server()


def test_scp_association():
    ae = AE(ae_title="Test AE")
    ae.add_requested_context(VerificationSOPClass)

    assoc = ae.associate(config.SCP_HOST, config.SCP_PORT, ae_title=config.SCP_AE_TITLE)
    assert assoc.is_established

    assoc.release()


def test_scp_association_rejected():
    ae = AE(ae_title="Test AE")
    ae.add_requested_context(VerificationSOPClass)

    assoc = ae.associate(config.SCP_HOST, config.SCP_PORT, ae_title="randomAET")
    assert not assoc.is_established

    assoc.release()


def test_same_ae_connect():
    ae = AE(ae_title="Test Multiple")
    ae.add_requested_context(VerificationSOPClass)

    assoc = ae.associate(config.SCP_HOST, config.SCP_PORT, ae_title=config.SCP_AE_TITLE)
    assert assoc.is_established

    assoc_fail = ae.associate(
        config.SCP_HOST, config.SCP_PORT, ae_title=config.SCP_AE_TITLE
    )
    assert not assoc_fail.is_established

    assoc.release()
    assoc_fail.release()


def test_scp_pipeline_association():
    ae = AE(ae_title="Test AE")
    ae.add_requested_context(VerificationSOPClass)

    assoc = ae.associate(config.SCP_HOST, config.SCP_PORT, ae_title="RVP-my-pipe")
    assert assoc.is_established

    assoc.release()


def test_echo():
    ae = AE(ae_title="Test AE")
    ae.add_requested_context(VerificationSOPClass)

    association = ae.associate(config.SCP_HOST, config.SCP_PORT, ae_title="RVU-Echo")

    assert association.is_established

    status = association.send_c_echo()
    assert status

    association.release()


def test_store_global(db, stub_broker, stub_worker):
    # Ensure no DicomNodes in test data
    db.query(DicomNode).delete()
    db.commit()

    assert os.path.exists(
        mock_path := os.path.join(os.path.dirname(__file__), "mock_data")
    )
    association = get_association_to_ae(config.SCP_AE_TITLE)

    uids_added = []
    for root, _, files in os.walk(mock_path):
        for file in files:
            if file.endswith(".dcm"):
                ds = dcmread(os.path.join(root, file))
                uid = ds.SeriesInstanceUID

                if (
                    series := models.dicom.DicomSeries.query(db)
                    .filter_by(series_instance_uid=uid)
                    .all()
                ):
                    [s.delete(db) for s in series]
                    db.commit()

                status = association.send_c_store(ds)
                assert status
                uids_added.append(uid)

    association.release()
    sleep(1)
    join(stub_broker, stub_worker)

    assert (node := db.query(DicomNode).first())
    assert node.user_id is None  # Node should not be tied to one user
    for uid in uids_added:
        assert (
            models.dicom.DicomSeries.query(db)
            .filter_by(series_instance_uid=uid)
            .first()
        ), f"Could not find series_instance_uid={uid} in db"


def test_store_valid_user(db, stub_broker, stub_worker):
    # Ensure no DicomNodes in test data
    db.query(DicomNode).delete()
    db.commit()

    # Send dicom to user
    association = get_association_to_ae(
        config.USER_AE_PREFIX + utils.get_test_user(db).username
    )
    perform_store(association)

    sleep(
        1
    )  # Ensure detached SCP server has enough time to send job to worker before .join

    join(stub_broker, stub_worker)

    user = utils.get_test_user(db)
    assert db.query(DicomNode).filter_by(user_id=user.id).first()


def test_store_invalid_user(db, stub_broker, stub_worker):
    # Ensure no DicomNodes in test data
    db.query(DicomSeries).delete()
    prev_count = db.query(DicomSeries).count()
    db.commit()

    # Send dicom to user
    association = get_association_to_ae(config.USER_AE_PREFIX + "FAKE_NAME")
    perform_store(association)

    sleep(
        1
    )  # Ensure detached SCP server has enough time to send job to worker before .join

    join(stub_broker, stub_worker)

    new_count = db.query(DicomSeries).count()
    assert prev_count == new_count


def test_store_valid_pipeline_no_containers(db, stub_broker, stub_worker):
    pipeline_ae_title = "test_scp"
    insert_pipeline(db, "test", ae_title=pipeline_ae_title)

    init_pipeline_run_count = db.query(PipelineRun).count()

    association = get_association_to_ae(config.PIPELINE_AE_PREFIX + pipeline_ae_title)
    perform_store(association)
    join(stub_broker, stub_worker)

    # Ensure SCP server has time to process request and generate PipelineRun record
    try:
        assert init_pipeline_run_count < db.query(PipelineRun).count()
    except AssertionError:
        sleep(3)  # DB not updated, try waiting first
        assert init_pipeline_run_count < db.query(PipelineRun).count()


def test_store_pipeline_workflow(db, stub_broker, stub_worker, authorization_header):
    # Upload / build containers
    assert os.path.exists(
        mock_path := os.path.join(os.path.dirname(__file__), "mock_data")
    )
    assert os.path.exists(file_path := os.path.join(mock_path, "simple_container.zip"))
    assert os.path.isfile(file_path)

    container = create_and_test_container(db, file_path)
    build_container_foreground(container)

    # Create pipeline with containers
    pipeline_ae_title = "workflow"
    pipeline = insert_pipeline(db, "test", ae_title=pipeline_ae_title)
    add_container_to_pipeline(container, pipeline, authorization_header)

    # Run pipeline by uploading dicom
    db.query(PipelineRun).delete()
    db.commit()

    init_pipeline_run_count = db.query(PipelineRun).count()
    association = get_association_to_ae(config.PIPELINE_AE_PREFIX + pipeline_ae_title)

    perform_store(association)

    sleep(
        2
    )  # Ensure detached SCP server has enough time to send job to worker before .join

    join(stub_broker, stub_worker)

    assert init_pipeline_run_count < db.query(PipelineRun).count()
    assert db.query(PipelineRun).first().status == "complete"

    delete_and_test_container(db, container)


def test_store_invalid_pipeline(db, stub_broker, stub_worker):
    init_pipeline_run_count = db.query(PipelineRun).count()

    association = get_association_to_ae(config.PIPELINE_AE_PREFIX + "Fake_AE")
    perform_store(association)
    join(stub_broker, stub_worker)

    assert init_pipeline_run_count == db.query(PipelineRun).count()


@mark.not_written
def test_store_same_instance(db, association):
    assert os.path.exists(
        mock_path := os.path.join(os.path.dirname(__file__), "mock_data")
    )

    uid_list = []
    for root, _, files in os.walk(mock_path):
        for file in files:
            if file.endswith(".dcm"):
                ds = dcmread(os.path.join(root, file))
                uid = ds.SeriesInstanceUID
                uid_list.append(uid)

                if (
                    series := models.dicom.DicomSeries.query(db)
                    .filter_by(series_instance_uid=uid)
                    .all()
                ):
                    [s.delete(db) for s in series]
                    db.commit()

                status = association.send_c_store(ds)
                assert status

                status = association.send_c_store(ds)
                assert status

    for uid in uid_list:
        # TODO: Should we be able to the same image twice?
        assert (
            len(
                models.dicom.DicomSeries.query(db)
                .filter_by(series_instance_uid=uid)
                .all()
            )
            == 1
        )


def get_association_to_ae(ae_title):

    # Create association to pipeline
    ae = AE(ae_title="test")
    ae.requested_contexts = StoragePresentationContexts
    assoc = ae.associate(config.SCP_HOST, config.SCP_PORT, ae_title=ae_title)

    assert assoc.is_established
    return assoc


def perform_store(
    association, mock_path=os.path.join(os.path.dirname(__file__), "mock_data")
):
    assert os.path.exists(mock_path)

    for root, _, files in os.walk(mock_path):
        for file in files:
            if file.endswith(".dcm"):
                ds = dcmread(os.path.join(root, file))

                status = association.send_c_store(ds)
                assert status

    association.release()


def add_container_to_pipeline(container, pipeline, authorization_header):
    response = client.put(
        f"/pipeline/{pipeline.id}",
        json={
            "pipeline_id": pipeline.id,
            "nodes": [
                {
                    "node_id": 0,
                    "container_id": container.id,
                    "x": 0,
                    "y": 0,
                    "container_is_input": False,
                    "container_is_output": False,
                    "destination_id": 0,
                }
            ],
            "links": [],
        },
        headers=authorization_header,
    )

    assert response.status_code == 200
