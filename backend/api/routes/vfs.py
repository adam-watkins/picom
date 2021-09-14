from typing import List
from os import path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session


from api import session, middleware, config
from api.auth import token_auth
from api.models.user import User
from api.models.pipeline import (
    PipelineRun,
    PipelineRunResultFile as ResultFile,
    Pipeline,
)
from api.schemas import BaseORMModel

router = APIRouter()


class FileSchema(BaseORMModel):
    pipeline_run_id: int
    filename: str
    type: str
    path: str


@router.get("", response_model=List[FileSchema])
def get_result_files(user: User = Depends(token_auth), db: Session = Depends(session)):
    files = (
        db.query(ResultFile)
        .join(PipelineRun)
        .join(Pipeline)
        .filter(Pipeline.user_id == user.id)
        .all()
    )

    return files


@router.get("/{file_id}")
@middleware.exists_or_404
def download_file(
    file_id: int, user: User = Depends(token_auth), db: Session = Depends(session)
):
    file: ResultFile = db.query(ResultFile).get(file_id)

    if not file or file.run.pipeline.user_id != user.id:
        raise False

    file_path = path.join(config.UPLOAD_DIR, file.path)
    file_bytes = open(file_path, "rb")
    response = StreamingResponse(file_bytes, media_type="application/octet-stream")
    response.headers["Content-Disposition"] = f"attachment; filename={file.filename}"

    return response


@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(session)):
    if file := db.query(ResultFile).get(file_id):
        file.delete(db)
