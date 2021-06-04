from pathlib import Path
from shutil import copytree

from pydicom import dcmread

from api.models.dicom import DicomNode
from api.models.pipeline import *
from api.services import DatabaseService


class PipelineConditionService(DatabaseService):
    _bucket: PipelineNodeStorageBucket = None
    _bucket_items: dict = None
    _starting_node: PipelineNode = None
    _conditions: List[PipelineNodeCondition] = None

    def __init__(self, pipeline: Pipeline, initiator: DicomNode, db):
        super().__init__()

        self.pipeline: Pipeline = pipeline
        self.initiator = initiator
        self._db = db

    @property
    def starting_node(self):
        if not self._starting_node:
            nodes = [n for n in self.pipeline.get_starting_nodes() if n.container_is_input]

            for node in nodes:
                if node.destination.is_rts:
                    self._starting_node = node
                elif self.initiator == node.destination:
                    self._starting_node = node
                    break

            # TODO: LOG no valid starting node

        return self._starting_node

    @property
    def storage_bucket(self) -> PipelineNodeStorageBucket:
        if self._bucket:
            return self._bucket

        kwargs = {
            "dicom_node_id": self.initiator.id,
            "pipeline_node_id": self.starting_node.id
        }

        if bucket := PipelineNodeStorageBucket.query(self._db).filter_by(**kwargs).first():
            self._bucket = bucket
        else:
            self._bucket = PipelineNodeStorageBucket(**kwargs).save(self._db)

        return self._bucket

    @property
    def bucket_items(self) -> dict:
        if not self._bucket_items:
            self._bucket_items = {item.tag: item for item in self.storage_bucket.items}

        return self._bucket_items

    def _create_bucket_item(self, tag: str) -> PipelineNodeStorageBucketItem:
        assert tag not in self.bucket_items

        item = PipelineNodeStorageBucketItem(
            pipeline_node_storage_bucket_id=self.storage_bucket.id,
            tag=tag,
        ).save(self._db)

        self._bucket_items[tag] = item
        return item

    def _update_bucket_item(self, tag, value):
        bucket_item = self.bucket_items.get(tag) or self._create_bucket_item(tag)

        if value not in bucket_item.values:
            # TODO: ADD DEBUG LOG?
            bucket_item.values = bucket_item.values + [str(value)]

    def has_conditions(self) -> bool:
        return bool(self.starting_node and self.starting_node.conditions)

    def add_series_to_storage_bucket(self, folder: Path):
        assert self.has_conditions()
        assert self.storage_bucket

        for file in folder.iterdir():
            assert file.is_file()

            ds = dcmread(str(file), stop_before_pixels=True)
            [self._update_bucket_item(c.tag, ds.get(c.tag)) for c in self.starting_node.conditions]

        copytree(folder, self._bucket.get_abs_path(), dirs_exist_ok=True)

    def are_conditions_met(self) -> bool:
        """
        Checks if the conditions to run a pipeline are satisfied
        :return: True if conditions are met else False
        """

        q = self._db.query(PipelineNodeStorageBucketItem, PipelineNodeCondition)\
            .join(PipelineNodeStorageBucket)\
            .filter(
                PipelineNodeCondition.pipeline_node_id == self.starting_node.id,
                PipelineNodeStorageBucketItem.tag == PipelineNodeCondition.tag
            )

        for bucket_item, condition in q.all():
            expected = set(condition.values)
            have = set(bucket_item.values)

            if condition.match.lower() == 'all' and not have.issuperset(expected):
                return False
            elif condition.match.lower() == 'any' and expected.isdisjoint(have):
                return False

        return True
