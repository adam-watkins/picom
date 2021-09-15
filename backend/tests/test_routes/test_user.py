import os

from api.models.user import User
from api.schemas.user import UserLocalCreate

from tests import client, testing_session, utils


def test_get_users_admin_only(authorization_header, db) -> list:
    response = client.get("/user/")
    assert response.status_code == 401

    response = client.get("/user/", headers=authorization_header)
    assert response.status_code == 401

    admin = UserLocalCreate(
        username="testAdmin",
        name="admin",
        password="pAssWord",
    )
    utils.create_local_user(**admin.dict())

    # Making sure the user is not an admin
    admin_auth = utils.get_auth_header(admin.username, admin.password)
    response = client.get("/user/me", headers=admin_auth)
    data = response.json()
    assert response.status_code == 200
    assert "is_admin" in data and not data["is_admin"]

    # Route should be admin only
    response = client.get("/user/", headers=admin_auth)
    assert response.status_code == 401

    # Making the user an admin
    user = User.query(db).filter_by(username=admin.username).first()
    assert user

    user.is_admin = True
    user.save(db)
    db.commit()

    # Making sure the user is an admin
    admin_auth = utils.get_auth_header(admin.username, admin.password)
    response = client.get("/user/me", headers=admin_auth)
    data = response.json()
    assert response.status_code == 200
    assert "is_admin" in data and data["is_admin"]

    # Route should be admin only
    response = client.get("/user/", headers=admin_auth)
    assert response.status_code == 200
    assert type(data := response.json()) is list and len(data)


def test_add_user():
    test_user = UserLocalCreate(
        username="joeSmith",
        name="Joe Smith",
        password="password",
    )

    with testing_session() as db:
        if user := db.query(User).filter_by(username=test_user.username).first():
            user.delete(db)
            db.commit()

    utils.create_local_user(**test_user.dict())
