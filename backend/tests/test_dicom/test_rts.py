from pathlib import Path
from time import sleep

from pydicom import dcmread
from pynetdicom import (
    AE,
    evt,
    AllStoragePresentationContexts,
    StoragePresentationContexts,
)

from api.queries.internal import get_return_to_sender
from api.schemas.dicom import DicomNode as DicomNodeSchema
from tests import client, config, mark
from tests.test_dicom.test_scp import perform_store, join
from tests.test_models.test_pipelines import LinearPipelineFactory

PORT = 11114


def custom_store_scp(ae_title, storage_folder, mock_path):
    def handle_store(event):
        ds = event.dataset
        ds.file_meta = event.file_meta
        ds.save_as(str(storage_folder / ds.SOPInstanceUID), write_like_original=False)
        return 0x0000

    def handle_release(event):
        compare_dcm_files(mock_files, storage_folder)

    handlers = [(evt.EVT_C_STORE, handle_store), (evt.EVT_RELEASED, handle_release)]

    ae = AE(ae_title=ae_title)
    ae.supported_contexts = AllStoragePresentationContexts

    return ae, handlers


def custom_store_scu(ae_title):
    ae = AE(ae_title=ae_title)
    ae.requested_contexts = StoragePresentationContexts

    return ae


def compare_dcm_files(mock_files: Path, received_files: Path):
    mock_datasets = {
        ds.SOPInstanceUID: ds for f in mock_files.glob("*.dcm") if (ds := dcmread(f))
    }
    received_datasets = {
        ds.SOPInstanceUID: ds
        for f in received_files.glob("*.dcm")
        if (ds := dcmread(f))
    }

    for SOPInstanceUID, ds in mock_datasets.items():
        assert SOPInstanceUID in received_datasets
        other = received_datasets[SOPInstanceUID]

        assert hasattr(ds, "pixel_array")
        assert hasattr(other, "pixel_array")

        assert ds.pixel_array.shape == other.pixel_array.shape
        assert (ds.pixel_array == other.pixel_array).all()


# TODO: this test only works like once a minute
@mark.skip()
def test_return_to_sender(
    db, stub_broker, stub_worker, authorization_header, tmp_folder, mock_path
):

    factory = LinearPipelineFactory(db, "rts_pipeline", ae_title="RTS")
    rts_container = DicomNodeSchema.from_orm(get_return_to_sender(db))
    factory.add_output_container(rts_container)
    pipeline = factory.create_pipeline(client, authorization_header)

    pipeline_aet = config.PIPELINE_AE_PREFIX + pipeline["ae_title"]

    # Sending images
    ae = custom_store_scu("RTS")
    assoc = ae.associate(
        config.SCP_HOST, config.SCP_PORT, ae_title=pipeline_aet, bind_address=("", PORT)
    )
    assert assoc.is_established
    perform_store(assoc, mock_path)
    assoc.release()

    # Starting the RTS server
    scp, handlers = custom_store_scp(
        "RTS", storage_folder=tmp_folder, mock_path=mock_path
    )
    scp.start_server(("", PORT), evt_handlers=handlers, block=False)

    # Ensure detached SCP server has enough time to send job to worker before .join
    sleep(2)
    join(stub_broker, stub_worker)
    scp.shutdown()
