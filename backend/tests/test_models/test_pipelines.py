import os
import pathlib
import pytest

from networkx.exception import NetworkXNoCycle
from networkx.algorithms.cycles import find_cycle
from networkx.algorithms.components import is_connected

from api.models.pipeline import *
from api.models.container import Container
from api.models.user import User

from api.schemas.container import Container as ContainerSchema
from api.schemas.pipeline import PipelineNodeCreate as PipelineNodeCreateSchema
from api.schemas.dicom import DicomNode as DicomNodeSchema

from tests import utils, mark, config


class LinearPipelineFactory:
    def __init__(self, db, pipeline_name, **kwargs):
        self.pipeline = insert_pipeline(db, pipeline_name, **kwargs)
        self.nodes = []
        self.edges = []
        self.db = db

    def add_container(
        self, container: ContainerSchema, destination: DicomNodeSchema = None
    ) -> ContainerSchema:
        node = PipelineNodeCreateSchema(
            node_id=len(self.nodes),
            container_id=container.id,
            container_is_input=container.is_input_container,
            container_is_output=container.is_output_container,
            x=0,
            y=0,
            dicom_node_id=destination.id,
        )

        if self.nodes:
            self.edges.append((self.nodes[-1]["node_id"], node.node_id))

        self.nodes.append(node.dict())

        return container

    def add_output_container(self, destination: DicomNodeSchema) -> ContainerSchema:
        container = (
            self.db.query(Container)
            .join(User)
            .filter(
                User.name == config.INTERNAL_USERNAME, Container.is_output_container
            )
            .first()
        )

        assert container
        schema = ContainerSchema.from_orm(container)

        return self.add_container(schema, destination)

    def create_pipeline(self, client, authorization_header):
        response = client.put(
            f"/pipeline/{self.pipeline.id}",
            json={
                "pipeline_id": self.pipeline.id,
                "nodes": self.nodes,
                "links": [{"from": src, "to": dest} for src, dest in self.edges],
            },
            headers=authorization_header,
        )

        assert response.status_code == 200
        return response.json()


def insert_pipeline(db, name, **kwargs) -> Pipeline:
    user = utils.get_test_user(db)
    pipeline = Pipeline(user_id=user.id, name=name, **kwargs)
    pipeline.save(db)
    db.commit()

    assert pipeline.id
    assert pipeline.user_id

    return pipeline


def insert_run(db, pipeline, **kwargs) -> PipelineRun:
    run = PipelineRun(pipeline_id=pipeline.id, **kwargs)
    run.save(db)
    db.commit()

    assert run.id
    assert run.pipeline_id

    return run


def insert_job(db, run, **kwargs) -> PipelineJob:
    job = PipelineJob(pipeline_run_id=run.id, **kwargs)
    job.save(db)
    db.commit()

    assert job.id
    assert job.pipeline_run_id

    return job


def test_pipeline_model(db):
    pipeline = insert_pipeline(db, "test")

    assert not pipeline.runs
    assert not pipeline.nodes
    assert not pipeline.links
    assert (
        type(pipeline.get_starting_nodes()) is list
        and not pipeline.get_starting_nodes()
    )

    pipeline.delete(db)
    db.commit()


def test_pipeline_run(db):
    pipeline = insert_pipeline(db, "Test Pipeline run")
    run = insert_run(db, pipeline)

    assert os.path.exists(run_path := run.get_abs_path())
    assert os.path.isdir(run_path)

    run.delete(db)
    assert not os.path.exists(run_path)

    db.commit()


def test_pipeline_job(db):
    pipeline = insert_pipeline(db, "Test Pipeline job")
    run = insert_run(db, pipeline)
    job = insert_job(db, run)

    assert os.path.exists(job_path := job.get_abs_path())
    assert os.path.isdir(job_path)

    job.delete(db)
    assert not os.path.exists(job_path)

    db.commit()


# noinspection DuplicatedCode
@mark.no_SQLLite
def test_cascade_delete_pipeline(db):
    pipeline = insert_pipeline(db, "test_cascade_delete_pipeline")
    run = insert_run(db, pipeline)
    job = insert_job(db, run)

    run_path = run.get_abs_path()
    job_path = job.get_abs_path()

    assert os.path.exists(run_path)
    assert os.path.exists(job_path)

    pipeline.delete(db)
    db.commit()

    assert not PipelineRun.query(db).get(run.id)
    assert not PipelineJob.query(db).get(job.id)

    assert not os.path.exists(run_path)
    assert not os.path.exists(job_path)


# noinspection DuplicatedCode
@mark.no_SQLLite
def test_cascade_delete_run(db):
    pipeline = insert_pipeline(db, "test_cascade_delete_run")
    run = insert_run(db, pipeline)
    job = insert_job(db, run)

    run_path = run.get_abs_path()
    job_path = job.get_abs_path()

    assert os.path.exists(run_path)
    assert os.path.exists(job_path)

    run.delete(db)
    db.commit()

    assert Pipeline.query(db).get(pipeline.id)
    assert not PipelineRun.query(db).get(run.id)
    assert not PipelineJob.query(db).get(job.id)

    assert not os.path.exists(run_path)
    assert not os.path.exists(job_path)


def test_job_volumes_paths(db):
    pipeline = insert_pipeline(db, "test_job_volumes_paths")
    run = insert_run(db, pipeline)
    job = insert_job(db, run)

    in_v = str(job.get_volume_abs_input_path())
    out_v = str(job.get_volume_abs_output_path())

    assert os.path.exists(in_v)
    assert os.path.exists(out_v)

    # Making sure the paths are not windows paths and linux paths
    assert not ("\\" in in_v and "/" in in_v)
    assert not ("\\" in out_v and "/" in out_v)


def test_linux_paths(db):
    pipeline = insert_pipeline(db, "test_linux_paths")
    run = insert_run(db, pipeline)
    job = insert_job(db, run)

    assert "\\" not in run.input_path
    assert "\\" not in run.output_path
    assert pathlib.Path(run.input_path).as_posix() == run.input_path
    assert pathlib.Path(run.output_path).as_posix() == run.output_path

    assert "\\" not in job.input_path
    assert "\\" not in job.output_path
    assert pathlib.Path(job.input_path).as_posix() == job.input_path
    assert pathlib.Path(job.output_path).as_posix() == job.output_path


def test_graphs(db):
    pipeline = insert_pipeline(db, "test_graphs")
    dg = pipeline.to_graph()

    assert len(dg.nodes) == 0
    assert len(dg.edges) == 0

    n1 = PipelineNode(pipeline_id=pipeline.id)
    n2 = PipelineNode(pipeline_id=pipeline.id)
    n1.save(db)
    n2.save(db)

    l1 = PipelineLink(pipeline_id=pipeline.id, from_node_id=n1.id, to_node_id=n2.id)
    l1.save(db)

    db.commit()

    assert len(pipeline.nodes) == 2
    assert len(pipeline.links) == 1

    dg = pipeline.to_graph()
    assert len(dg.nodes) == len(pipeline.nodes)
    assert len(dg.edges) == len(pipeline.links)
    assert dg.is_directed()

    with pytest.raises(NetworkXNoCycle):
        find_cycle(dg)

    assert is_connected(dg.to_undirected())
