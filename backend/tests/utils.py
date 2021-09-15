from tests import models, config, schemas, TEST_USER, client


def create_local_user(name, username, password) -> schemas.user.User:
    user_to_create = schemas.user.UserLocalCreate(
        name=name, username=username, password=password
    )
    response = client.post("/user/", json=user_to_create.dict())
    data = response.json()

    assert response.status_code == 200
    assert data["username"] == user_to_create.username
    assert data["name"] == user_to_create.name
    assert not data["is_admin"]

    return schemas.user.User(**data)


# noinspection PyUnboundLocalVariable
def get_auth_header(username: str, password: str) -> dict:
    response = client.post(
        "/auth/token", data={"username": username, "password": password}
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data and type(token := data["access_token"]) is str

    return {"Authorization": f"Bearer {token}"}


def get_current_user(client, authorization_header):
    me = client.get("/user/me")
    assert me.status_code == 200

    return me.json()


def get_test_user(db) -> models.user.User:
    assert (
        user := db.query(models.user.User)
        .filter_by(username=TEST_USER.username)
        .first()
    )

    return user
