import os
import pathlib

from api.routes.container import create_container, delete_container
from api.models.container import Container

from tests import testing_session, utils


# noinspection DuplicatedCode
def test_container_create_zip(db):
    assert os.path.exists(
        mock_path := os.path.join(os.path.dirname(__file__), "mock_data")
    )
    assert os.path.exists(file_path := os.path.join(mock_path, "simple_container.zip"))
    assert os.path.isfile(file_path)

    container = create_and_test_container(db, file_path)
    assert type(container) is Container
    delete_and_test_container(db, container)


def create_and_test_container(db, file_path, **kwargs):
    with open(file_path, "rb") as fp:
        data = fp.read()

    container = create_container(
        auto_build=kwargs.get("auto_build", False),
        file=data,
        name=kwargs.get("name", "test_container_create_zip"),
        filename=kwargs.get("filename", "simple_container.zip"),
        description=kwargs.get("description", "A simple container"),
        is_input_container=kwargs.get("is_input_container", False),
        is_output_container=kwargs.get("is_output_container", False),
        is_shared=kwargs.get("is_shared", False),
        user=utils.get_test_user(db),
        db=db,
    )

    assert type(container) is not list
    assert type(container) is Container
    assert pathlib.Path(container.get_abs_path()).exists()
    assert not pathlib.Path(container.get_path()).is_absolute()
    assert (
        container.dockerfile_path == pathlib.Path(container.dockerfile_path).as_posix()
    )
    return container


def delete_and_test_container(db, container):
    assert type(container) is Container
    abs_path = container.get_abs_path()
    delete_container(container.id, db)
    assert not pathlib.Path(abs_path).exists()
