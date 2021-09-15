import os
import pydicom
from pydicom import dcmread

INPUT_DIR = os.environ["RAIVEN_INPUT_DIR"]
OUTPUT_DIR = os.environ["RAIVEN_OUTPUT_DIR"]


def person_names_callback(dataset, data_element):
    if data_element.VR == "PN":
        data_element.value = "anonymous"


def curves_callback(dataset, data_element):
    if data_element.tag.group & 0xFF00 == 0x5000:
        del dataset[data_element.tag]


def anonymize_ds(dataset):
    dataset.PatientID = "REMOVED"
    dataset.walk(person_names_callback)
    dataset.walk(curves_callback)
    dataset.remove_private_tags()

    if "OtherPatientIDs" in dataset:
        delattr(dataset, "OtherPatientIDs")

    if "OtherPatientIDsSequence" in dataset:
        del dataset.OtherPatientIDsSequence

    tag = "PatientBirthDate"
    if tag in dataset:
        dataset.data_element(tag).value = "19000101"

    return dataset


if __name__ == "__main__":
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            if file.endswith(".dcm"):
                ds = dcmread(os.path.join(root, file))
                ds = anonymize_ds(ds)
                ds.save_as(os.path.join(OUTPUT_DIR, file))
