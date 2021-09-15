from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api import session, queries
from api.auth import token_auth
from api.dicom import scu
from api.models.dicom import DicomNode, DicomPatient, DicomStudy, DicomSeries
from api.models.user import User
from api.schemas import dicom

router = APIRouter()


@router.get("/echo", response_model=None)
def c_echo(host: str, port: int, title: str):
    """Performs a DICOM c_echo to dicom node"""

    node = DicomNode(title=title, host=host, port=port)

    if not scu.send_echo(node):
        raise HTTPException(503, "C-Echo Failed")


@router.get("/received-series")
def get_received_series(db: Session = Depends(session)):
    """Getting the number of received DICOM series in the past 7 days. Used in the DicomTrendChart"""
    # TODO: Add index on date received and only query the last 7 days
    return queries.group_by_date(db, DicomSeries.date_received)


@router.get("/series-breakdown/{dicom_type}/{dicom_id}")
def get_series_breakdown(
    dicom_type: str, dicom_id: int, db: Session = Depends(session)
):
    """Getting the breakdown of Dicom modalities. Used for the horizontal breakdown charts"""
    q = db.query(DicomSeries.modality, func.count(DicomSeries.modality))
    q, cls = {
        "Node": (q.join(DicomStudy).join(DicomPatient).join(DicomNode), DicomNode),
        "Patient": (q.join(DicomStudy).join(DicomPatient), DicomPatient),
        "Study": (q.join(DicomStudy), DicomStudy),
        "Series": (q, DicomSeries),
    }.get(dicom_type)

    dicom_modality_count = (
        q.group_by(DicomSeries.modality).filter(cls.id == dicom_id).all()
    )
    return {modality: count for modality, count in dicom_modality_count}


@router.get("/stats", response_model=dicom.DicomStats)
def get_dicom_stats(db: Session = Depends(session)):
    """Getting counts for the DICOM images. Used in the dashboard counters"""
    stats = {
        "dicom_node_counts": db.query(DicomNode).count(),
        "dicom_patient_counts": db.query(DicomPatient).count(),
        "dicom_study_counts": db.query(DicomStudy).count(),
        "dicom_series_counts": db.query(DicomSeries).count(),
    }
    return stats


@router.get("/nodes", response_model=List[dicom.DicomNode])
def get_all_dicom_nodes(
    input_node: bool = None,
    output_node: bool = None,
    rts: bool = False,
    user: User = Depends(token_auth),
    db: Session = Depends(session),
):
    """Get all DICOM nodes"""
    q = db.query(DicomNode).filter(
        or_(DicomNode.user_id == user.id, DicomNode.user_id == None)
    )

    if input_node is not None:
        q = q.filter(DicomNode.input == input_node)

    if output_node is not None:
        q = q.filter(DicomNode.output == output_node)

    nodes: List[DicomNode] = q.all()

    if rts:
        nodes.insert(0, queries.internal.get_return_to_sender(db))

    return nodes


@router.post("/nodes")
def create_dicom_node(
    node: dicom.DicomNodeCreate,
    user: User = Depends(token_auth),
    db: Session = Depends(session),
):
    """Create a dicom node"""
    q = db.query(DicomNode).filter_by(title=node.title, host=node.host, port=node.port)

    if not (db_node := q.first()):
        db_node = DicomNode(**node.dict(), user_id=user.id)
        db_node.save(db)
        return db_node

    # Update to a output node
    elif not db_node.output:
        db_node.output = True
        return db_node

    else:
        raise HTTPException(422, "Node already exists")


@router.get("/nodes/{dicom_node_id}/patients", response_model=List[dicom.DicomPatient])
def get_node_patients(dicom_node_id: int, db: Session = Depends(session)):
    """Get a DICOM node's patients"""
    return db.query(DicomPatient).filter_by(dicom_node_id=dicom_node_id).all()


@router.get(
    "/nodes/{dicom_node_id}/patient/{patient_id}/studies",
    response_model=List[dicom.DicomStudy],
)
def get_patient_studies(
    dicom_node_id: int, patient_id: int, db: Session = Depends(session)
):
    """Get a patient's studies"""
    return db.query(DicomStudy).filter_by(dicom_patient_id=patient_id).all()


@router.get(
    "/patient/{patient_id}/study/{study_id}/series",
    response_model=List[dicom.DicomSeries],
)
def get_study_series(patient_id: int, study_id: int, db: Session = Depends(session)):
    """Get a study's series"""
    return db.query(DicomSeries).filter_by(dicom_study_id=study_id).all()


@router.delete("/node/{dicom_node_id}", response_model=dicom.DicomNode)
def delete_node(dicom_node_id: int, db: Session = Depends(session)):
    """Delete a node"""
    return db.query(DicomNode).get(dicom_node_id).delete(db)


@router.delete("/patient/{patient_id}", response_model=dicom.DicomPatient)
def delete_patient(patient_id: int, db: Session = Depends(session)):
    """Delete a patient"""
    return db.query(DicomPatient).get(patient_id).delete(db)


@router.delete("/study/{study_id}", response_model=dicom.DicomStudy)
def delete_study(study_id: int, db: Session = Depends(session)):
    """Delete a study"""
    return db.query(DicomStudy).get(study_id).delete(db)


@router.delete("/series/{series_id}", response_model=dicom.DicomSeries)
def delete_series(series_id: int, db: Session = Depends(session)):
    """Delete a series"""
    return db.query(DicomSeries).get(series_id).delete(db)
