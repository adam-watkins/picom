import io

from api.schemas.container import ContainerCreate

from tests import client, utils


def test_add_container(
    authorization_header,
    form_data: dict = None,
    user_id: int = None,
    file: bytes = None,
) -> dict:
    if not form_data:
        form_data = {
            "user_id": user_id,
            "name": "Default Container",
            "description": "A Default Container",
            "filename": "Dockerfile",
            "is_input_container": False,
            "is_output_container": False,
            "is_shared": False,
        }

    if not user_id:
        me = client.get("/user/me", headers=authorization_header)
        assert me.status_code == 200
        form_data["user_id"] = me.json()["id"]

    form_data["file"] = file if file else (io.BytesIO(b"test bytes"), "test.jpg")
    response = client.post("/container/", data=form_data, headers=authorization_header)

    assert response.status_code == 200
    return response.json()


def test_get_containers(authorization_header) -> dict:
    response = client.get("/container/", headers=authorization_header)
    assert response.status_code == 200
    assert type(response.json()) is list
