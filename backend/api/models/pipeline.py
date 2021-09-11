import pathlib
from datetime import datetime
from typing import List

from networkx import DiGraph
from sqlalchemy import *
from sqlalchemy.orm import relationship

from api import config
from . import Base, PathMixin, TimestampMixin, IOPathMixin, CASCADE


class Pipeline(Base):
    user_id = Column(ForeignKey("user.id", **CASCADE))
    name = Column(String)
    ae_title = Column(String, unique=True)
    is_shared = Column(Boolean, default=False)

    runs: List["PipelineRun"] = relationship(
        "PipelineRun", backref="pipeline", passive_deletes=True)
    nodes: List["PipelineNode"] = relationship(
        "PipelineNode", backref="pipeline")
    links: List["PipelineLink"] = relationship(
        "PipelineLink", backref="pipeline")

    def get_starting_nodes(self):
        return [n for n in self.nodes if n.is_root_node()]

    def to_graph(self) -> DiGraph:
        graph = DiGraph()
        graph.add_nodes_from([v.id for v in self.nodes])
        graph.add_edges_from([(e.from_node_id, e.to_node_id)
                             for e in self.links])

        return graph


class PipelineNodeStorageBucket(PathMixin, Base):
    pipeline_node_id = Column(ForeignKey("pipeline_node.id", **CASCADE))
    dicom_node_id = Column(ForeignKey("dicom_node.id", **CASCADE))

    items = relationship("PipelineNodeStorageBucketItem",
                         cascade='all, delete-orphan')


class PipelineNodeStorageBucketItem(Base):
    pipeline_node_storage_bucket_id = Column(
        ForeignKey("pipeline_node_storage_bucket.id", **CASCADE))
    tag = Column(String)

    if 'sqlite' not in config.SQLALCHEMY_DATABASE_URI.lower():
        values = Column(ARRAY(String), default=[])

    def __repr__(self, **kwargs) -> str:
        return super().__repr__(tag=self.tag, values=self.values, **kwargs)


class PipelineNode(Base):
    pipeline_id = Column(ForeignKey("pipeline.id", **CASCADE))
    container_id = Column(ForeignKey("container.id"))
    dicom_node_id = Column(ForeignKey("dicom_node.id"))
    x_coord = Column(Integer)
    y_coord = Column(Integer)
    container_is_input = Column(Boolean)
    container_is_output = Column(Boolean)

    destination = relationship("DicomNode", uselist=False)
    container = relationship("Container", uselist=False)
    next_links = relationship(
        'PipelineLink', foreign_keys='PipelineLink.from_node_id')
    previous_links = relationship(
        'PipelineLink', foreign_keys='PipelineLink.to_node_id')
    jobs = relationship('PipelineJob', backref='node')
    conditions = relationship("PipelineNodeCondition", backref="node")
    storage_buckets = relationship("PipelineNodeStorageBucket", backref='node')

    def is_root_node(self):
        return not len(self.previous_links)

    def is_leaf_node(self):
        return not len(self.next_links)

    def get_next_nodes(self):
        return [link.next_node for link in self.next_links]

    def __repr__(self, **kwargs) -> str:
        return super().__repr__(root=self.is_root_node(), leaf=self.is_leaf_node(), **kwargs)


class PipelineNodeCondition(Base):
    pipeline_node_id = Column(ForeignKey("pipeline_node.id", **CASCADE))
    tag = Column(String)
    match = Column(String)

    if 'sqlite' not in config.SQLALCHEMY_DATABASE_URI.lower():
        values = Column(ARRAY(String))


class PipelineLink(Base):
    pipeline_id = Column(ForeignKey("pipeline.id", **CASCADE))
    to_node_id = Column(ForeignKey("pipeline_node.id", **CASCADE))
    from_node_id = Column(ForeignKey("pipeline_node.id", **CASCADE))

    next_node = relationship(
        'PipelineNode', foreign_keys='PipelineLink.to_node_id', uselist=False)
    previous_node = relationship(
        'PipelineNode', foreign_keys='PipelineLink.from_node_id', uselist=False)

    def __repr__(self, **kwargs) -> str:
        return super().__repr__(to_node=self.to_node_id, from_node=self.from_node_id, **kwargs)


class PipelineRun(IOPathMixin, Base):
    pipeline_id = Column(ForeignKey('pipeline.id', **CASCADE))
    initiator_id = Column(ForeignKey("dicom_node.id"), nullable=True)
    status = Column(String, default='Created')

    created_datetime = Column(DateTime, default=datetime.now)
    finished_datetime = Column(DateTime)

    jobs = relationship('PipelineJob', backref="run",
                        cascade='all, delete-orphan')
    initiator = relationship('DicomNode')
    files = relationship('PipelineRunResultFile',
                         backref="run", cascade='all, delete-orphan')

    def __repr__(self, **kwargs) -> str:
        return f'<Pipeline ID: {self.pipeline_id}, Initiator ID: {self.initiator_id}>'


class PipelineJob(IOPathMixin, TimestampMixin, Base):
    pipeline_run_id = Column(ForeignKey("pipeline_run.id", **CASCADE))
    pipeline_node_id = Column(ForeignKey("pipeline_node.id", **CASCADE))
    status = Column(String)
    exit_code = Column(Integer)

    error = relationship('PipelineJobError', backref="job", uselist=False)

    def get_volume_abs_input_path(self):
        return pathlib.Path(config.UPLOAD_VOLUME_ABSPATH) / self.input_path

    def get_volume_abs_output_path(self):
        return pathlib.Path(config.UPLOAD_VOLUME_ABSPATH) / self.output_path

    def __repr__(self, **kwargs) -> str:
        return f'<Pipeline Run ID: {self.pipeline_run_id}, Pipeline Node ID: {self.pipeline_node_id}, Status: {self.status}>'


class PipelineJobError(Base):
    pipeline_job_id = Column(ForeignKey("pipeline_job.id", ondelete="CASCADE"))
    stderr = Column(String)


class PipelineRunResultFile(Base):
    pipeline_run_id = Column(ForeignKey("pipeline_run.id", **CASCADE))
    filename = Column(String)
    type = Column(String)
    path = Column(String)
