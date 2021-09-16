import re
from datetime import datetime
from typing import Union

from docker.models.containers import Container as DockerContainer

from api import config, models
from api.models.pipeline import PipelineJob, PipelineJobError, PipelineRun
from api.pipelining._tasks import HOST_PATH_TYPE


def validate_tag(tag: str) -> str:
    """
    TODO: Implement A Regex for this validation
    Name components may contain lowercase letters, digits and separators.
    A separator is defined as a period, one or two underscores, or one or more dashes.
    A name component may not start or end with a separator.v
    https://docs.docker.com/engine/reference/commandline/tag/#extended-description
    """
    tag = tag.lower()

    return re.sub("[!\"#$%&'()*+,/:;<=>?@[\\]^`{|}~ \t\n\r\x0b\x0c]", "", tag)


def get_volumes(job: PipelineJob) -> dict:
    """Creates the volumes to be mounted to the running container"""

    return {
        HOST_PATH_TYPE(job.get_volume_abs_input_path()): {
            "bind": config.RAIVEN_INPUT_DIR,
            "mode": "ro",
        },
        HOST_PATH_TYPE(job.get_volume_abs_output_path()): {
            "bind": config.RAIVEN_OUTPUT_DIR,
            "mode": "rw",
        },
    }


def get_environment(job: PipelineJob) -> dict:
    """Builds a dictionary of environment varibales to be passed to the running container"""
    initiator = job.run.initiator

    return {
        "RAIVEN_INITIATOR_AET": initiator.title if initiator else None,
        "RAIVEN_INITIATOR_HOST": initiator.host if initiator else None,
        "RAIVEN_INPUT_DIR": config.RAIVEN_INPUT_DIR,
        "RAIVEN_OUTPUT_DIR": config.RAIVEN_OUTPUT_DIR,
    }


def create_job(
    db, pipeline_run_id: int, pipeline_node_id: int, status: str = "Created"
) -> PipelineJob:
    return PipelineJob(
        pipeline_run_id=pipeline_run_id,
        pipeline_node_id=pipeline_node_id,
        status=status,
    ).save(db)


def mark_job_complete(
    db,
    job: PipelineJob,
    exit_code: int = None,
    status: str = "exited",
    stderr: Union[DockerContainer, str] = "An Error Occurred",
) -> PipelineJob:
    job.update(db, exit_code=exit_code, status=status)

    if job.exit_code != 0:
        if type(stderr) is DockerContainer:
            stderr.reload()
            stderr = stderr.logs(stdout=False, stderr=True).decode("utf-8")

        job_error = PipelineJobError(pipeline_job_id=job.id, stderr=stderr)
        job_error.save(db)

    return job


def mark_run_complete(db, job: PipelineJob, status: str = "complete") -> PipelineRun:
    """Marks the pipeline RUN (not job) complete"""

    run = job.run
    models.utils.copy_model_fs(job, run, dst_subdir="output", final_node=True)

    run.update(db, status=status, finished_datetime=datetime.now())

    return run
