import os
import pathlib
from datetime import datetime
from shutil import rmtree

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import Session
from inflection import underscore, pluralize

from api import config

CASCADE = {"ondelete": "CASCADE"}


class _Base:
    id = Column(Integer, primary_key=True, index=True)

    @declared_attr
    def __tablename__(self):
        return underscore(self.__name__)

    @classmethod
    def query(cls, session):
        return session.query(cls)

    def save(self, session: Session):
        session.add(self)
        self._flush(session)
        return self

    def update(self, session: Session, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self._flush(session)
        return self

    def delete(self, session: Session):
        session.delete(self)
        self._flush(session)

    def detach(self, session: Session):
        session.expunge(self)

    # noinspection PyMethodMayBeStatic
    def _flush(self, session: Session):
        try:
            session.flush()
        except DatabaseError:
            session.rollback()
            raise

    def __repr__(self, **kwargs) -> str:
        info = "".join(f"{k}={v} " for k, v in kwargs.items()).strip()
        return f'<{self.__class__.__name__} id={self.id}{" " if info else ""}{info}>'


Base = declarative_base(cls=_Base)


class NestedPathMixin(object):
    @staticmethod
    def to_abs_path(rel_path):
        return os.path.join(config.UPLOAD_DIR, rel_path)

    def get_path(self) -> str:
        raise NotImplementedError(
            f"{type(self)} must implement get_path as it is a subclass of NestedPathMixin"
        )

    def get_abs_path(self, **kwargs) -> str:
        return self.to_abs_path(self.get_path())

    def save(self, *args, **kwargs):
        """Will Create a new directory upon completion"""

        super().save(*args, **kwargs)
        if not os.path.exists(path := self.get_abs_path()):
            os.makedirs(path)

        return self

    def delete(self, *args, **kwargs):
        """Will Delete a new directory upon completion"""

        super().delete(*args, **kwargs)
        if os.path.exists(path := self.get_abs_path()):
            rmtree(path)


class PathMixin(NestedPathMixin):
    @declared_attr
    def __directory__(self) -> str:
        """The naming scheme for the folder containing all the objects"""

        return pluralize(self.__tablename__)

    @declared_attr
    def __absolute_directory__(self) -> str:
        return pathlib.Path(config.UPLOAD_DIR) / self.__directory__

    def get_path(self) -> pathlib.Path:
        if not self.id:
            raise Exception("The object needs to be first saved in the db")

        return pathlib.Path(self.__directory__) / str(self.id)


class IOPathMixin(PathMixin):
    _INPUT_DIRNAME = "input"
    _OUTPUT_DIRNAME = "output"

    input_path = Column(String)
    output_path = Column(String)

    def save(self, *args, create_folders: bool = True, **kwargs):
        super().save(*args, **kwargs)

        # Making folders
        if create_folders:
            abs_path = self.get_abs_path()
            for dirname in [self._INPUT_DIRNAME, self._OUTPUT_DIRNAME]:
                if not os.path.exists(p := os.path.join(abs_path, dirname)):
                    os.makedirs(p)

            # Saving Path info
            rel_path = self.get_path()
            self.input_path = (rel_path / self._INPUT_DIRNAME).as_posix()
            self.output_path = (rel_path / self._OUTPUT_DIRNAME).as_posix()
            super().save(*args, **kwargs)

        return self

    def get_abs_path(self, subdir: str = None) -> str:
        if subdir == "input":
            return self.get_abs_input_path()
        elif subdir == "output":
            return self.get_abs_output_path()
        else:
            return super().get_abs_path()

    def get_abs_input_path(self):
        return os.path.join(config.UPLOAD_DIR, self.input_path)

    def get_abs_output_path(self):
        return os.path.join(config.UPLOAD_DIR, self.output_path)


class TimestampMixin(object):
    timestamp = Column(DateTime, default=datetime.utcnow)
