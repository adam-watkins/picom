from datetime import datetime
from typing import List, Optional
from pydantic import validator, root_validator
from networkx import DiGraph

from api.models import dicom, Base
from api.pipelining.utils import validate_pipeline_structure

from . import BaseModel, BaseORMModel
from .container import Container
from .dicom import DicomNode


class PipelineStats(BaseModel):
    pipeline_counts: int
    pipeline_run_counts: int


class PipelineNodeConditionCreate(BaseModel):
    match: str = "All"
    tag: str
    values: List[str]


class PipelineNodeCondition(PipelineNodeConditionCreate, BaseORMModel):
    pipeline_node_id: int


class PipelineNodeCreate(BaseModel):
    node_id: int
    container_id: int
    x: int
    y: int
    container_is_input: bool
    container_is_output: bool
    dicom_node_id: Optional[int]
    conditions: Optional[List[PipelineNodeConditionCreate]] = []

    @root_validator
    def check_io_node_has_destination(cls, values):
        if values.get("container_is_input"):
            assert values.get("dicom_node_id"), "Input Node Missing an Input Source"

        if values.get("container_is_output"):
            assert values.get(
                "dicom_node_id"
            ), "Output Node Missing an Output Destination"

        return values


class PipelineNode(BaseORMModel):
    pipeline_id: int
    container_id: int
    dicom_node_id: Optional[int]
    x_coord: int
    y_coord: int
    container_is_input: bool
    container_is_output: bool

    container: Container
    destination: Optional[DicomNode]
    conditions: Optional[List[PipelineNodeCondition]] = []


class PipelineLinkCreate(BaseModel):
    to: int
    from_: int

    class Config:
        fields = {"from_": "from"}


class PipelineLink(BaseORMModel):
    pipeline_id: int
    to_node_id: int
    from_node_id: int


class PipelineCreate(BaseModel):
    name: str
    ae_title: Optional[str]
    is_shared: bool = False


class PipelineUpdate(BaseModel):
    pipeline_id: Optional[int]
    nodes: Optional[List[PipelineNodeCreate]] = []
    links: Optional[List[PipelineLinkCreate]] = []

    @root_validator
    def check_pipeline_structure(cls, values):
        graph = DiGraph()
        graph.add_nodes_from([v.node_id for v in values.get("nodes")])
        graph.add_edges_from([(e.from_, e.to) for e in values.get("links")])
        validate_pipeline_structure(graph)

        return values

    @validator("nodes")
    def unique_node_ids(cls, v):
        s = set([node.node_id for node in v])
        assert len(s) == len(v), "Pipeline cannot contain duplicate nodes_ids"

        return v


class Pipeline(PipelineCreate, BaseORMModel):
    user_id: Optional[int]
    name: str


class PipelineCondition(BaseORMModel):
    condition_name: str
    conditions: dict
    is_active: bool
    pipeline_id: int
    pipeline: Pipeline


class PipelineFull(Pipeline):
    nodes: Optional[List[PipelineNode]] = []
    links: Optional[List[PipelineLink]] = []


class PipelineId(BaseModel):
    pipeline_id: int


class PipelineRunOptions(BaseModel):
    _DICOM_TYPES = {
        "node": dicom.DicomNode,
        "patient": dicom.DicomPatient,
        "study": dicom.DicomStudy,
        "series": dicom.DicomSeries,
    }

    pipeline_id: Optional[int]
    dicom_obj_type: str
    dicom_obj_id: str

    class Config:
        schema_extra = {
            "example": {
                "dicom_obj_type": "study",
                "dicom_obj_id": "some study id",
            }
        }

    @validator("dicom_obj_type")
    def type_must_be(cls, v: str):
        if v.lower() not in cls._DICOM_TYPES.keys():
            raise ValueError(
                f"{v} is not a valid type. Valid types are {cls.DICOM_TYPES.keys()}"
            )
        return v

    def get_cls_type(self) -> Base:
        return self._DICOM_TYPES[self.dicom_obj_type.lower()]


class PipelineJobError(BaseORMModel):
    stderr: str


class PipelineJob(BaseORMModel):
    pipeline_run_id: str
    pipeline_node_id: Optional[int]

    timestamp: datetime
    input_path: str
    status: Optional[str]
    output_path: str
    exit_code: Optional[str]
    error: Optional[PipelineJobError]


class PipelineRun(BaseORMModel):
    id: int
    status: str
    created_datetime: datetime
    finished_datetime: Optional[datetime]

    # optional for now becaues don't want to mess up the other pipeline run stuff
    # but should save pipeline name with the pipeline run, because if pipeline gets
    # deleted, then the PipelineRun will error since it has no associated Pipeline anymore
    pipeline: Optional[Pipeline]

    jobs: Optional[List[PipelineJob]]


class PipelineJobErrorAdditionalInfo(BaseORMModel):
    run: PipelineRun
    node: PipelineNode


class PipelineJobErrorFull(BaseORMModel):
    stderr: str
    job: PipelineJobErrorAdditionalInfo
