from docker.models.containers import Container as DockerContainer
import pathlib

from api import config, worker_session, models
from api.dicom.scu import send_dicom_folder
from api.models.pipeline import (
    PipelineRun,
    PipelineJob,
    PipelineJobError,
    PipelineNode,
    PipelineRunResultFile,
)

from . import docker, dramatiq
from .utils import (
    get_volumes,
    get_environment,
    create_job,
    mark_job_complete,
    mark_run_complete,
)


def _run_next_nodes(job: PipelineJob, run_id: int):
    for node in job.node.get_next_nodes():

        try:
            # TODO: Clean this up variable naming
            if node.container_is_output:
                dicom_output_task.send_with_options(args=(run_id, node.id, job.id))
            else:
                run_node_task.send_with_options(args=(run_id, node.id, job.id))
        except Exception as e:
            print(e)


@dramatiq.actor(max_retries=0)
def run_node_task(run_id: int, node_id: int, previous_job_id: int = None):
    with worker_session() as db:

        # TODO: Check if all previous nodes have finished
        # TODO: TEMP fix for input nodes
        node: PipelineNode = db.query(PipelineNode).get(node_id)
        if node.container_is_input:
            for n in node.get_next_nodes():
                run_node_task.send_with_options(args=(run_id, n.id))
            return

        job: PipelineJob = create_job(db, run_id, node_id)

        if not (build := job.node.container.build):
            # TODO: ABORT AND BUILD
            print("Cant run node because container is not built")
            return

        if previous_job_id:
            src_subdir = "output"
            prev = db.query(PipelineJob).get(previous_job_id)
        else:
            src_subdir = "input"
            prev = db.query(PipelineRun).get(run_id)

        models.utils.copy_model_fs(prev, job, src_subdir=src_subdir)
        volumes = get_volumes(job)
        environment = get_environment(job)

        container: DockerContainer = docker.containers.run(
            image=build.tag,
            detach=True,
            volumes=volumes,
            environment=environment,
            labels=["Raiven"],
        )

        job.update(db, status="running")
        db.commit()

        # Long running task
        print("Waiting for container")
        exit_code = container.wait()["StatusCode"]
        print("Container finished with exit code", exit_code)

        job = mark_job_complete(db, job, exit_code=exit_code, stderr=container)
        if job.exit_code != 0:
            mark_run_complete(db, job, status="error")

        elif job.node.is_leaf_node():
            post_run_cleanup(db, job)

        else:
            _run_next_nodes(job, run_id)

        # Cleaning Up Container
        container.remove()


@dramatiq.actor(max_retries=3)
def dicom_output_task(run_id: int, node_id: int, previous_job_id: int = None):
    with worker_session() as db:
        job = create_job(db, run_id, node_id)

        if not (dest := job.node.destination):
            job.update(db, status="failed", exit_code=-1)
            PipelineJobError(
                pipeline_job_id=job.id, stderr="No Destination for the pipeline"
            ).save(db)
            return

        if previous_job_id:
            prev: PipelineJob = PipelineJob.query(db).get(previous_job_id)
            folder = prev.get_abs_output_path()
        else:
            prev: PipelineRun = db.query(PipelineRun).get(run_id)
            folder = prev.get_abs_input_path()

        # Return to sender
        if dest.host == config._RTS_HOST and dest.port == config._RTS_PORT:
            dest = job.run.initiator

        # Long running task
        send_dicom_folder(dest, folder)

        mark_job_complete(db, job, exit_code=0)
        mark_run_complete(db, job)


def post_run_cleanup(db, job: PipelineJob):
    print("Pipeline finished")
    mark_run_complete(db, job)

    run: PipelineRun = job.run
    output_path = pathlib.Path(run.get_abs_output_path())
    for file in output_path.iterdir():
        PipelineRunResultFile(
            pipeline_run_id=run.id,
            filename=file.name,
            type=file.stem if file.is_file() else "folder",
            path=str(file.relative_to(config.UPLOAD_DIR)),
        ).save(db)
