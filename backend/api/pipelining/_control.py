import pathlib
import shutil

from api import config
from api.models import utils
from api.models.pipeline import PipelineRun
from ._tasks import build, run, test, ingest


def run_test_task():
    test.run_test_task.send()


class ContainerController:
    """Class that houses the controllers for building containers"""

    @staticmethod
    def build_container(container_id: int, priority: int = 1):
        build.build_container_task.send_with_options(
            args=(container_id,), priority=priority
        )


class PipelineController:
    """Class that houses the controllers for running and creating pipeline runs"""

    @staticmethod
    def run_pipeline_task(db, pipeline_run: PipelineRun, priority: int = 1) -> bool:
        """Run a specific Pipeline with default priority of 1
        For each starting node in  the pipeline, the node task is enqueued onto the worker node
        Args:
            db: Database session (dependency injection)
            pipeline_run: PipelineRun to run
            priority (int): Priority in the queue
        Returns:
            Bool: Currently, always returns true
        """

        pipeline_run.status = "running"
        pipeline_run.save(db)
        db.commit()

        for node in pipeline_run.pipeline.get_starting_nodes():
            task = (
                run.dicom_output_task if node.container_is_output else run.run_node_task
            )
            args = pipeline_run.id, node.id

            task.send_with_options(args=args, priority=priority)

        return True

    @staticmethod
    def run_pipeline_on_folder(
        db, pipeline_id: str, folder: pathlib.Path, initiator_dicom_node_id: int = None
    ) -> bool:
        pipeline_run = PipelineRun(
            pipeline_id=pipeline_id, initiator_id=initiator_dicom_node_id
        )
        pipeline_run.save(db)

        # Copy temp files to pipeline input and commit
        shutil.copytree(
            folder.resolve(), pipeline_run.get_abs_input_path(), dirs_exist_ok=True
        )
        shutil.rmtree(folder.resolve())
        db.commit()

        return PipelineController.run_pipeline_task(db, pipeline_run)

    @staticmethod
    def pipeline_run_factory(
        db, dicom_cls, dicom_obj_id: int, pipeline_id: int
    ) -> PipelineRun:
        """Create and return a PipelineRun instance
        In the process, also copies the input/output folder from upload jobs to upload runs

        Args:
            db: Database session (dependency injection)
            dicom_cls: Dicom Class to Query
            dicom_obj_id (int): Object ID
            pipeline_id (int): Pipeline ID to run
        Returns:
            PipelineRun: Instance of Pipeline to run
        """
        pipeline_run = PipelineRun(pipeline_id=pipeline_id)
        pipeline_run.save(db)

        input_data_model = dicom_cls.query(db).get(dicom_obj_id)
        utils.copy_model_fs(input_data_model, pipeline_run)

        return pipeline_run


class DicomIngestController:
    TASK = ingest.run_ingest_task.send_with_options

    class EmptyFolderException(Exception):
        pass

    @staticmethod
    def _execute_task(*args) -> bool:
        return DicomIngestController.TASK(args=args)

    @staticmethod
    def ingest_to_storage(folder: str, dicom_node_id: int, user_id: int = None) -> bool:
        return DicomIngestController._execute_task(folder, dicom_node_id, user_id)
