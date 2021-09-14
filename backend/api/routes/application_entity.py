from typing import List
from pydantic import BaseModel

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from api import session, models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ApplicationEntity])
def get_application_entities(db: Session = Depends(session)):
    return db.query(models.dicom.ApplicationEntity).all()


@router.post("/", response_model=schemas.ApplicationEntity)
def create_application_entity(
    ae: schemas.ApplicationEntityCreate, db: Session = Depends(session)
):
    return models.dicom.ApplicationEntity(title=ae.title).save(db)


@router.get("/{application_entity_id}", response_model=schemas.ApplicationEntity)
def get_application_entity(application_entity_id: int, db: Session = Depends(session)):
    return db.query(models.dicom.ApplicationEntity).get(application_entity_id)


@router.delete("/{application_entity_id}", response_model=schemas.ApplicationEntity)
def delete_application_entity(
    application_entity_id: int, db: Session = Depends(session)
):
    return (
        db.query(models.dicom.ApplicationEntity).get(application_entity_id).delete(db)
    )
