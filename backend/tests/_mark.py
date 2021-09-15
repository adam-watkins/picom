from pytest import mark as _mark

from . import config as cfg

not_written = _mark.skip(reason="Test not written")
no_SQLLite = _mark.skipif(
    "sqlite" in cfg.SQLALCHEMY_DATABASE_URI.lower(),
    reason="SQLite Does not support this test",
)

skip = _mark.skip
skipif = _mark.skipif
