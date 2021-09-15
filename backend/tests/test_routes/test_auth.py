from time import sleep

from tests import client, utils, TEST_USER, config


def create_header(token):
    return {"Authorization": token}


def test_login():
    username = "test_login"
    password = "test_password"

    user = utils.create_local_user("test", username, password)
    assert user

    response = client.post(
        "/auth/token", data={"username": user.username, "password": password}
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data and type(token := data["access_token"]) is str

    response = client.get("/user/me")
    assert response.status_code == 401

    # noinspection PyUnboundLocalVariable
    response = client.get("/user/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_login_failure():
    username = "test_failure"
    password = "my_password"
    user = utils.create_local_user("test", username, password)

    response = client.post(
        "/auth/token", data={"username": user.username, "password": password}
    )
    assert response.status_code == 200

    response = client.post(
        "/auth/token", data={"username": user.username, "password": password + "sds"}
    )
    assert response.status_code == 401

    response = client.post(
        "/auth/token", data={"username": user.username, "password": password[:-2]}
    )
    assert response.status_code == 401

    response = client.post(
        "/auth/token",
        data={"username": user.username.replace("_", ""), "password": password},
    )
    assert response.status_code == 401


def test_login_empty():
    response = client.post("/auth/token", data={"username": "", "password": ""})
    assert response.status_code in [401, 422]


def test_login_no_body():
    response = client.post("/auth/token")
    assert response.status_code == 422


def test_invalid_token(authorization_header):
    response = client.get("/user/me", headers=authorization_header)
    assert response.status_code == 200

    response = client.get("/user/me", headers=create_header("broken_token"))
    assert response.status_code == 401

    response = client.get("/user/me", headers=create_header("bearer broken_token"))
    assert response.status_code == 401


def test_expired_token(custom_serializer, db):
    test_user = utils.get_test_user(db)
    token = test_user.generate_token()

    sleep(1)
    assert not custom_serializer.verify_token(token)


# noinspection DuplicatedCode, PyUnboundLocalVariable, PyUnusedLocal
def test_expired_token_api_call(custom_serializer):
    user = utils.create_local_user("test", "ZeroLifeToken", "expired-token")
    assert user

    response = client.post(
        "/auth/token", data={"username": "ZeroLifeToken", "password": "expired-token"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data and type(token := data["access_token"]) is str

    sleep(1)
    assert client.get("/user/me", headers=create_header(token)).status_code == 401
