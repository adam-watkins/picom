import pathlib
import posixpath
import pytest

from tests import models, testing_session


def test_nested_path():
    # noinspection PyAbstractClass
    class TestNestedPathModel(models.Base, models.NestedPathMixin):
        pass

    mixin = TestNestedPathModel()

    with pytest.raises(NotImplementedError):
        mixin.get_abs_path()

    with pytest.raises(NotImplementedError):
        mixin.get_path()


def test_path_mixin():
    class TestPathModel(models.Base, models.PathMixin):
        pass

    mixin = TestPathModel()
    assert mixin.__directory__
    assert mixin.__absolute_directory__
    assert pathlib.Path(mixin.__absolute_directory__)
