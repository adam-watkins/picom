import pathlib
import shutil

from api import config
from api.models import utils
from api.models.pipeline import Pipeline
from api.models.user import User
from api.pipelining import PipelineController, DicomIngestController

from . import DatabaseService, PipelineConditionService, DicomNodeService


class DicomIngestService(DatabaseService):
    class EmptyFolderException(Exception):
        pass

    def __init__(
        self,
        folder: pathlib.Path,
        called_aet: str,
        calling_aet: str,
        calling_host: str,
    ):
        super().__init__()

        self.folder = folder
        self.called_aet = called_aet
        self.calling_aet = calling_aet
        self.calling_host = calling_host
        self.initiator_node = None
        self._action = None

        # Pushed to pipeline
        if self.called_aet.startswith(config.PIPELINE_AE_PREFIX):
            self._action = self._ingest_through_pipeline

        # Pushed to user or Globally
        elif (
            self.called_aet.startswith(config.USER_AE_PREFIX)
            or self.called_aet == config.SCP_AE_TITLE
        ):
            self._action = self._ingest_to_storage

        # Pushed to an undefined location
        else:
            raise ValueError("ERROR: Undefined called AET")

    def __enter__(self):
        super().__enter__()

        self.initiator_node = DicomNodeService(self._db).get_from_connection(
            self.calling_aet, self.calling_host
        )
        assert self.initiator_node

        return self

    def execute(self):
        if not any(self.folder.iterdir()):
            shutil.rmtree(self.folder.resolve())

            # TODO: Better logging
            print("INFO: Empty ingested folder")
            raise self.EmptyFolderException("An Ingest Folder Cannot Be Empty")

        self._action()

    def _get_rel_folder(self) -> str:
        return self.folder.relative_to(config.UPLOAD_DIR).as_posix()

    def _get_user_id(self) -> int:
        if not self.called_aet.startswith(config.USER_AE_PREFIX):
            return None

        username = utils.strip_prefix(self.called_aet, config.USER_AE_PREFIX)
        user = self._db.query(User).filter_by(username=username).first()

        if not user:
            raise ValueError("User %s not found" % username)

        return user.id

    def _ingest_to_storage(self):
        return DicomIngestController.ingest_to_storage(
            folder=self._get_rel_folder(),
            dicom_node_id=self.initiator_node.id,
            user_id=self._get_user_id(),
        )

    def _run_pipeline(self, pipeline, folder) -> bool:
        return PipelineController.run_pipeline_on_folder(
            db=self._db,
            pipeline_id=pipeline.id,
            folder=pathlib.Path(folder),
            initiator_dicom_node_id=self.initiator_node.id,
        )

    def _run_pipeline_bucket(
        self, pipeline, conditions_service: PipelineConditionService
    ) -> bool:
        print(
            f"Running folder through pipeline: '{pipeline.ae_title}' from storage bucket"
        )
        ret = self._run_pipeline(
            pipeline, conditions_service.storage_bucket.get_abs_path()
        )
        conditions_service.storage_bucket.delete(self._db)

        return ret

    def _ingest_through_pipeline(self) -> bool:
        ae_title = utils.strip_prefix(self.called_aet, config.PIPELINE_AE_PREFIX)
        pipeline = self._db.query(Pipeline).filter_by(ae_title=ae_title).first()
        folder = self.folder

        if not pipeline:
            raise ValueError(
                f"ERROR: Attempted to ingest to non-existant pipeline {ae_title}"
            )

        # Evaluate Conditions to see if we should run the pipeline
        conditions_service = PipelineConditionService(
            pipeline, self.initiator_node, self._db
        )
        if conditions_service.has_conditions():
            conditions_service.add_series_to_storage_bucket(self.folder)

            # Delete the tmp_folder now that we have copied to the bucket
            shutil.rmtree(self.folder)

            # Run if all the conditions are satisfied
            if conditions_service.are_conditions_met():
                return self._run_pipeline_bucket(pipeline, conditions_service)

            else:
                print(
                    f"Waiting for more files before running pipeline: '{pipeline.ae_title}'"
                )
                return False

        # No condition, run pipeline
        else:
            print(f"Running folder through pipeline: '{pipeline.ae_title}'")
            return self._run_pipeline(pipeline, folder)
