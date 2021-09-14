import os

from pydicom import dcmread
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import CTImageStorage


def upload_folder(upload_dir, upload_ae_title):
    """Small test program that uploads an entire dicom directory to a node"""

    ae = AE(ae_title="BC158VIPT1")
    ae.requested_contexts = StoragePresentationContexts

    assoc = ae.associate("localhost", 11112, ae_title=upload_ae_title)
    if assoc.is_established:
        print("ESTABLISHED")

        for root, _, files in os.walk(upload_dir):
            for file in files:
                if file.endswith(".dcm"):
                    ds = dcmread(os.path.join(root, file))
                    status = assoc.send_c_store(ds)
                    if not status:
                        print(
                            "Connection timed out, was aborted or received invalid response"
                        )
    else:
        print("Not established")

    assoc.release()


if __name__ == "__main__":
    # Replace with your own absolute path to a test folder
    UPLOAD_DIR = "E:\\BCCRC\\dicom\\pyPET4RT"
    # Replace with title of desired AE. RAIVEN for default
    UPLOAD_AE_TITLE = "RVP-test"

    upload_folder(UPLOAD_DIR, UPLOAD_AE_TITLE)
