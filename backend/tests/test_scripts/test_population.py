from tests import config, models


def get_default_user(db) -> models.user.User:
    users = (
        db.query(models.user.User).filter_by(username=config.INTERNAL_USERNAME).all()
    )
    assert len(users) == 1
    assert type(user := users[0]) == models.user.User
    assert user.username == config.INTERNAL_USERNAME

    return user


def get_default_containers(db):
    user = get_default_user(db)
    return models.container.Container.query(db).filter_by(user_id=user.id).all()


def test_default_user(db) -> int:
    get_default_user(db)


def test_default_containers(db):
    containers = get_default_containers(db)
    assert len(containers) == len(config.DEFAULT_CONTAINERS)

    for container in containers:
        assert container.is_shared
