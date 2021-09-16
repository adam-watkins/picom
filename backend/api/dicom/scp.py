import pathlib
import uuid

from pydicom.filewriter import write_file_meta_info
from pynetdicom import AE, evt, debug_logger
from pynetdicom.presentation import AllStoragePresentationContexts
from pynetdicom.sop_class import VerificationSOPClass

from api import config, logger
from api.pipelining import DicomIngestController
from api.services import DicomNodeService, DicomIngestService

# debug_logger()

# Use a hash map
CONNECTIONS = {}

REJECTED_PERMANENT = 0x01
REJECTED_TRANSIENT = 0x02
SOURCE_SERVICE_USER = 0x01
SOURCE_PROVIDER_USER = 0x03
DIAG_CALLING_AET_NOT_RECOGNIZED = 0x03
DIAG_CALLED_AET_NOT_RECOGNIZED = 0x07
DIAG_LOCAL_LIMIT_EXCEEDED = 0x02


def encode_aet(ae_title_bytes: bytes) -> str:
    return str(ae_title_bytes, encoding="utf-8").strip()


def get_ae_titles(event):
    return (
        encode_aet(event.assoc.requestor.primitive.calling_ae_title),
        encode_aet(event.assoc.requestor.primitive.called_ae_title),
    )


def handle_association_request(event):
    requestor_ae_title, called_ae_title = get_ae_titles(event)

    print("handle associate request hit")

    with DicomNodeService() as node_service:
        node_service.update_or_create_from_connection(
            title=requestor_ae_title,
            host=event.assoc.requestor.address,
            implementation_version_name=encode_aet(
                event.assoc.requestor.implementation_version_name
            ),
        )

    # TODO: Not in list of allowed connections and allow push to pipe
    if not is_valid_ae_title(called_ae_title):
        event.assoc.acse.send_reject(
            REJECTED_PERMANENT, SOURCE_SERVICE_USER, DIAG_CALLED_AET_NOT_RECOGNIZED
        )
        logger.log(
            f"REJECTED REQUEST ASSOCIATION FROM {requestor_ae_title} DUE TO UNKNOWN CALLED AET: {called_ae_title}"
        )

    # ALREADY CONNECTED
    elif requestor_ae_title in CONNECTIONS:
        event.assoc.acse.send_reject(
            REJECTED_TRANSIENT, SOURCE_PROVIDER_USER, DIAG_LOCAL_LIMIT_EXCEEDED
        )
        logger.log(
            f"REJECTED REQUEST ASSOCIATION FROM {requestor_ae_title} AS IT IS ALREADY CONNECTED"
        )
    else:
        path = pathlib.Path(config.UPLOAD_DIR) / "tmp" / str(uuid.uuid1())
        CONNECTIONS[requestor_ae_title] = path
        path.mkdir(parents=True)
        logger.log(f"ACCEPTED REQUEST ASSOCIATION FROM {requestor_ae_title}")


def is_valid_ae_title(called_ae_title):
    is_global_ae_title = config.SCP_AE_TITLE in called_ae_title
    has_valid_ae_title_prefix = called_ae_title.startswith(config.VALID_AE_PREFIXES)

    return is_global_ae_title or has_valid_ae_title_prefix


def handle_association_release(event):
    """Upon release start a task for all the received files to be ingested into the db"""

    requestor_ae_title, called_ae_title = get_ae_titles(event)
    calling_host, calling_port = (
        event.assoc.requestor.address,
        event.assoc.requestor.port,
    )

    if requestor_ae_title in CONNECTIONS:
        try:
            with DicomIngestService(
                folder=CONNECTIONS[requestor_ae_title],
                calling_aet=requestor_ae_title,
                calling_host=calling_host,
                called_aet=called_ae_title,
            ) as ingest:
                ingest.execute()

        except DicomIngestController.EmptyFolderException:
            """No C Store was performed"""
            pass
        except Exception as e:
            print(e)
        finally:
            del CONNECTIONS[requestor_ae_title]

    return 0x0000


def handle_store(event):
    """Handles EVT_C_STORE"""
    requestor_ae_title, called_ae_title = get_ae_titles(event)

    path = CONNECTIONS[requestor_ae_title] / (
        event.request.AffectedSOPInstanceUID + ".dcm"
    )
    with open(path, "wb") as f:
        f.write(b"\x00" * 128)
        f.write(b"DICM")
        # TODO: check this is still needed
        # event.file_meta.TransferSyntaxUID = uid.ImplicitVRLittleEndian
        write_file_meta_info(f, event.file_meta)
        f.write(event.request.DataSet.getvalue())

    return 0x0000


class SCP:
    _handlers = [
        (evt.EVT_REQUESTED, handle_association_request),
        (evt.EVT_RELEASED, handle_association_release),
        (evt.EVT_C_STORE, handle_store),
    ]

    def __init__(self, ae_title="PICOM_SCP", host="localhost", port=11112, debug=False):
        self.ae_title = ae_title
        self.host = host
        self.port = port

        self._ae = AE(ae_title)
        self._ae.supported_contexts = AllStoragePresentationContexts
        self._ae.add_supported_context(VerificationSOPClass)

        # if debug:
        #     debug_logger()

    def start_server(self, blocking=False):
        msg = f"Starting DICOM SCP {self.ae_title} on port {self.port}"
        logger.info(msg)
        print(msg)

        self._ae.start_server(
            (self.host, self.port), block=blocking, evt_handlers=self._handlers
        )

    def stop_server(self):
        self._ae.shutdown()

    def get_ae(self) -> AE:
        return self._ae


if __name__ == "__main__":
    print("Starting server...")
    print("Waiting for connections...")
    scp = SCP()
    scp.start_server(blocking=False)
    scp.stop_server()
