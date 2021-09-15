from tests import client, testing_session, utils, TEST_USER, schemas, mark
from tests.test_routes.test_container import test_add_container


def test_get_stats(authorization_header):
    response = client.get("/pipeline/stats")
    assert response.status_code == 401

    response = client.get("/pipeline/stats", headers=authorization_header)
    assert response.status_code == 200


def test_get_runs_graph(authorization_header):
    response = client.get("/pipeline/runs", headers=authorization_header)
    assert response.status_code == 200


def test_get_results(authorization_header):
    response = client.get("/pipeline/results", headers=authorization_header)
    assert response.status_code == 200


@mark.not_written
def test_download_run():
    pass


def test_download_run_dne(authorization_header):
    response = client.get("/pipeline/download/", headers=authorization_header)
    assert response.status_code != 200

    response = client.get("/pipeline/download/-1", headers=authorization_header)
    assert response.status_code == 404

    response = client.get("/pipeline/download/0", headers=authorization_header)
    assert response.status_code == 404


@mark.not_written
def test_download_run_another_users():
    raise NotImplementedError


def test_get_all_pipelines(authorization_header):
    response = client.get("/pipeline/", headers=authorization_header)
    assert response.status_code == 200
    assert type(response.json()) is list

    return response.json()


def test_create_pipeline(
    authorization_header, pipeline=schemas.pipeline.PipelineCreate(name="test-pipeline")
):
    # Create
    before = test_get_all_pipelines(authorization_header)
    response = client.post(
        "/pipeline/", headers=authorization_header, json=pipeline.dict()
    )
    data = response.json()
    after = test_get_all_pipelines(authorization_header)

    assert response.status_code == 200
    assert len(after) == len(before) + 1
    assert data["name"] == pipeline.name

    response = client.get(f'/pipeline/{data["id"]}', headers=authorization_header)
    assert response.status_code == 200

    return response.json()


def test_create_pipeline_cyclic(authorization_header):
    container = test_add_container(authorization_header)
    pipeline_schema = schemas.pipeline.PipelineCreate(name="cyclic-pipeline")
    pipeline = test_create_pipeline(authorization_header, pipeline_schema)

    data = {
        "pipeline_id": pipeline["id"],
        "nodes": [
            {
                "node_id": 0,
                "container_id": container["id"],
                "x": 0,
                "y": 0,
                "container_is_input": False,
                "container_is_output": False,
                "destination_id": 0,
            }
        ],
        "links": [{"to": 0, "from": 0}],
    }

    url = f'/pipeline/{pipeline["id"]}'
    response = client.put(url, json=data, headers=authorization_header)

    assert response.status_code == 422

    return response.json()


def test_create_pipeline_disconnected(authorization_header):
    container = test_add_container(authorization_header)
    pipeline_schema = schemas.pipeline.PipelineCreate(name="disconnected-pipeline")
    pipeline = test_create_pipeline(authorization_header, pipeline_schema)

    data = {
        "pipeline_id": pipeline["id"],
        "nodes": [
            {
                "node_id": 0,
                "container_id": container["id"],
                "x": 0,
                "y": 0,
                "container_is_input": False,
                "container_is_output": False,
                "destination_id": 0,
            },
            {
                "node_id": 1,
                "container_id": container["id"],
                "x": 0,
                "y": 0,
                "container_is_input": False,
                "container_is_output": False,
                "destination_id": 0,
            },
        ],
        "links": [],
    }

    url = f'/pipeline/{pipeline["id"]}'
    response = client.put(url, json=data, headers=authorization_header)

    assert response.status_code == 422

    return response.json()


def test_duplicated_node_ids(authorization_header):
    container = test_add_container(authorization_header)
    pipeline_schema = schemas.pipeline.PipelineCreate(name="disconnected-pipeline")
    pipeline = test_create_pipeline(authorization_header, pipeline_schema)

    data = {
        "pipeline_id": pipeline["id"],
        "nodes": [
            {
                "node_id": 0,
                "container_id": container["id"],
                "x": 0,
                "y": 0,
                "container_is_input": False,
                "container_is_output": False,
                "destination_id": 0,
            },
            {
                "node_id": 0,
                "container_id": container["id"],
                "x": 0,
                "y": 0,
                "container_is_input": False,
                "container_is_output": False,
                "destination_id": 0,
            },
        ],
        "links": [],
    }

    url = f'/pipeline/{pipeline["id"]}'
    response = client.put(url, json=data, headers=authorization_header)

    assert response.status_code == 422

    return response.json()


def test_create_pipeline_connected(authorization_header):
    container = test_add_container(authorization_header)
    pipeline_schema = schemas.pipeline.PipelineCreate(name="disconnected-pipeline")
    pipeline = test_create_pipeline(authorization_header, pipeline_schema)

    data = {
        "pipeline_id": pipeline["id"],
        "nodes": [
            {
                "node_id": 0,
                "container_id": container["id"],
                "x": 0,
                "y": 0,
                "container_is_input": False,
                "container_is_output": False,
                "destination_id": 0,
            },
        ],
        "links": [],
    }

    url = f'/pipeline/{pipeline["id"]}'
    response = client.put(url, json=data, headers=authorization_header)

    assert response.status_code == 200

    return response.json()


@mark.not_written
def test_update_pipeline(authorization_header):
    pipeline = schemas.pipeline.PipelineCreate(name="test-update")
    pipeline_id = test_create_pipeline(authorization_header, pipeline)["id"]

    assert pipeline_id

    # TODO: Finish this test
    raise NotImplementedError


def test_delete_pipeline(authorization_header):
    pipeline = schemas.pipeline.PipelineCreate(name="test-delete")
    pipeline_id = test_create_pipeline(authorization_header, pipeline)["id"]
    assert pipeline_id

    response = client.delete(f"/pipeline/{pipeline_id}", headers=authorization_header)
    assert response.status_code == 200

    response = client.get(f"/pipeline/{pipeline_id}", headers=authorization_header)
    assert response.status_code == 404


def test_delete_pipeline_dne(authorization_header):
    pipeline = schemas.pipeline.PipelineCreate(name="test-delete-dne")
    pipeline_id = test_create_pipeline(authorization_header, pipeline)["id"]
    assert pipeline_id

    response = client.delete(f"/pipeline/{pipeline_id}", headers=authorization_header)
    assert response.status_code == 200

    response = client.delete(f"/pipeline/{pipeline_id}", headers=authorization_header)
    assert response.status_code == 404
