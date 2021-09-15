import pytest

from tests import models, config


@pytest.fixture(scope="function")
def custom_serializer():
    models.user.User._set_serializer("my key", 0)

    yield models.user.User

    models.user.User._set_serializer(config.SECRET_KEY, config.TOKEN_TTL)
