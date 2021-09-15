import os
import shutil
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api import session, queries, middleware
from api.pipelining import PipelineController
from api.models.pipeline import (
    Pipeline,
    PipelineLink,
    PipelineNode,
    PipelineRun,
    PipelineJob,
    PipelineJobError,
    PipelineNodeCondition,
)
from api.schemas import pipeline as schemas
from api.models.user import User
from api.auth import token_auth

router = APIRouter()


@router.get("/errors", response_model=List[schemas.PipelineJobErrorFull])
def get_pipeline_errors(db: Session = Depends(session)):
    """Get all pipeline job errors"""
    return db.query(PipelineJobError).all()


@router.delete("/error/{error_id}", response_model=schemas.PipelineJobErrorFull)
@middleware.exists_or_404
def delete_pipeline_error(error_id: int, db: Session = Depends(session)):
    """Delete a pipeline job error"""
    if pipeline_error := db.query(PipelineJobError).get(error_id):
        pipeline_error.delete(db)
    return pipeline_error


@router.get("/stats", response_model=schemas.PipelineStats)
def get_pipeline_stats(db: Session = Depends(session)):
    """
    Getting total number of pipelines and pipelines.
    Used for the dashboard counters
    """
    stats = {
        "pipeline_counts": db.query(Pipeline).count(),
        "pipeline_run_counts": db.query(PipelineRun).count(),
    }
    return stats


@router.get("/runs")
def get_pipeline_runs_dashboard(limit: int = 7, db: Session = Depends(session)):
    """
    Getting number of pipeline runs in the past 7 days.
    Used for the dashboard bar chart
    """
    return queries.group_by_date(db, PipelineRun.created_datetime, limit=limit)


@router.get("/results", response_model=List[schemas.PipelineRun])
def get_all_pipeline_runs(
    user: User = Depends(token_auth), db: Session = Depends(session)
):
    """Get the user's pipeline runs"""
    return (
        db.query(PipelineRun)
        .join(Pipeline)
        .filter(Pipeline.user_id == user.id)
        .order_by(PipelineRun.created_datetime)
        .all()
    )


@router.get("/{pipeline_id}/results", response_model=List[schemas.PipelineRun])
def get_pipeline_results(pipeline_id: int, db: Session = Depends(session)):
    """
    Get pipeline runs for a specific pipeline.
    Used in pipeline info
    """
    return db.query(PipelineRun).filter(pipeline_id == PipelineRun.pipeline_id).all()


@router.delete("/run/{pipeline_run_id}")
@middleware.exists_or_404
def get_pipeline_jobs(
    pipeline_run_id: int,
    user: User = Depends(token_auth),
    db: Session = Depends(session),
):
    """Deletes a pipeline and all its stored data"""
    if not (run := PipelineRun.query(db).get(pipeline_run_id)):
        return None

    pipeline = run.pipeline
    if not pipeline.is_shared and pipeline.user_id != user.id:
        raise HTTPException(403, "Don't Have Permissions to Delete These Files")

    [job.delete(db) for job in run.jobs]

    run.delete(db)
    return "Ok"


@router.get("/run/{pipeline_run_id}/jobs", response_model=List[schemas.PipelineJob])
def get_pipeline_jobs(pipeline_run_id: int, db: Session = Depends(session)):
    """
    Get all pipeline jobs for a pipeline run.
    Used in pipeline info
    """
    return (
        db.query(PipelineJob)
        .filter(PipelineJob.pipeline_run_id == pipeline_run_id)
        .all()
    )


@router.get(
    "/job/{pipeline_job_id}/errors", response_model=List[schemas.PipelineJobError]
)
def get_pipeline_job_errors(pipeline_job_id: int, db: Session = Depends(session)):
    """
    Get all pipeline errors for a pipeline job.
    Used in pipeline info treeview.
    """
    return (
        db.query(PipelineJobError)
        .filter(PipelineJobError.pipeline_job_id == pipeline_job_id)
        .all()
    )


@router.get("/job/node/{pipeline_node_id}", response_model=List[schemas.PipelineNode])
def get_pipeline_job_nodes(pipeline_node_id, db: Session = Depends(session)):
    """
    Get the pipeline node for a pipeline node.
    Used in pipeline info treeview.
    """
    return db.query(PipelineNode).filter(PipelineNode.id == pipeline_node_id).all()


@router.get(
    "/download/{pipeline_run_id}",
)
@middleware.exists_or_404
def download_pipeline_run(pipeline_run_id: int, db: Session = Depends(session)):
    """Downloading the pipeline run results in a zip file form"""
    pipeline_run: PipelineRun = db.query(PipelineRun).get(pipeline_run_id)
    if not pipeline_run:
        return False

    result_path = pipeline_run.get_abs_output_path()
    zip_path = os.path.join(pipeline_run.get_abs_path(), "result")

    # Creating a zip file if it doesn't exist
    if not os.path.exists(zip_path):
        shutil.make_archive(zip_path, "zip", result_path)

    # Sending the zip file as response
    zip_file = open(zip_path + ".zip", "rb")
    response = StreamingResponse(zip_file, media_type="application/x-zip-compressed")
    response.headers["Content-Disposition"] = "attachment; filename=results.zip"

    return response


@router.get("/", response_model=List[schemas.Pipeline])
def get_all_pipelines(user: User = Depends(token_auth), db: Session = Depends(session)):
    """Get current user's pipelines."""
    return (
        db.query(Pipeline)
        .filter((Pipeline.user_id == user.id) | Pipeline.is_shared)
        .all()
    )


@router.post("/", response_model=schemas.PipelineFull)
def create_pipeline(
    pipeline: schemas.PipelineCreate,
    user: User = Depends(token_auth),
    db: Session = Depends(session),
):
    """Create a new pipeline"""
    return (
        Pipeline(
            name=pipeline.name,
            ae_title=pipeline.ae_title,
            is_shared=pipeline.is_shared,
            user_id=user.id,
        )
    ).save(db)


@router.get("/{pipeline_id}", response_model=schemas.PipelineFull)
def get_pipeline(pipeline_id: int, db: Session = Depends(session)):
    if not (pipeline := db.query(Pipeline).get(pipeline_id)):
        raise HTTPException(404)

    return pipeline


@router.put("/{pipeline_id}/edit", response_model=schemas.Pipeline)
def edit_pipeline(
    pipeline_id: int, pipeline: schemas.PipelineCreate, db: Session = Depends(session)
):
    """Edit a pipeline"""
    pipeline_to_edit = db.query(Pipeline).get(pipeline_id)
    pipeline_to_edit.name = pipeline.name
    pipeline_to_edit.ae_title = pipeline.ae_title
    pipeline_to_edit.is_shared = pipeline.is_shared
    return pipeline_to_edit


@router.put("/{pipeline_id}/run", response_model=schemas.PipelineRun)
def run_pipeline(
    pipeline_id: int,
    run_options: schemas.PipelineRunOptions,
    db: Session = Depends(session),
):
    """Runs A Pipeline."""
    run = PipelineController.pipeline_run_factory(
        db, run_options.get_cls_type(), run_options.dicom_obj_id, pipeline_id
    )
    db.commit()

    PipelineController.run_pipeline_task(db, run)
    return run


@router.get("/{pipeline_id}/nodes", response_model=List[schemas.PipelineNode])
def get_pipeline_nodes(pipeline_id: int, db: Session = Depends(session)):
    """Get all nodes from a pipeline"""
    return db.query(PipelineNode).filter(PipelineNode.pipeline_id == pipeline_id).all()


@router.get("/{pipeline_id}/links")
def get_pipeline_links(pipeline_id: int, db: Session = Depends(session)):
    """Get all links from a pipeline"""
    return (
        db.query(PipelineLink).filter(PipelineLink.pipeline_id == pipeline_id).delete()
    )


@router.put("/{pipeline_id}", response_model=schemas.PipelineFull)
def update_pipeline(
    pipeline_id: int,
    pipeline_update: schemas.PipelineUpdate,
    db: Session = Depends(session),
):
    """This Allows you to update / add pipeline containers and links"""

    # clear out any previous nodes / links
    db.query(PipelineNode).filter(PipelineNode.pipeline_id == pipeline_id).delete()
    db.query(PipelineLink).filter(PipelineLink.pipeline_id == pipeline_id).delete()

    # save new nodes and links
    nodes = {}
    for n in pipeline_update.nodes:
        node = PipelineNode(
            pipeline_id=pipeline_id,
            container_id=n.container_id,
            dicom_node_id=n.dicom_node_id,
            x_coord=n.x,
            y_coord=n.y,
            container_is_input=n.container_is_input,
            container_is_output=n.container_is_output,
        ).save(db)
        nodes[n.node_id] = node

        # Save Conditions
        [
            PipelineNodeCondition(**c.dict(), pipeline_node_id=node.id).save(db)
            for c in n.conditions
        ]

    for link in pipeline_update.links:
        PipelineLink(
            pipeline_id=pipeline_id,
            to_node_id=nodes[link.to].id,
            from_node_id=nodes[link.from_].id,
        ).save(db)

    return db.query(Pipeline).get(pipeline_id)


@router.delete("/{pipeline_id}", response_model=schemas.Pipeline)
@middleware.exists_or_404
def delete_pipeline(pipeline_id: int, db: Session = Depends(session)):
    if pipeline := db.query(Pipeline).get(pipeline_id):
        pipeline.delete(db)

    return pipeline
