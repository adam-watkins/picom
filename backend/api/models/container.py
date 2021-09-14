import os

from sqlalchemy import *
from sqlalchemy.orm import relationship

from api import config
from . import Base, PathMixin, TimestampMixin, CASCADE
from api.models.pipeline import PipelineNode


class ContainerTags(Base):
    container_id = Column(ForeignKey("container.id", **CASCADE))
    tag_id = Column(ForeignKey("tag.id", **CASCADE))


class Container(PathMixin, Base):
    user_id = Column(ForeignKey("user.id", **CASCADE))
    name = Column(String)
    dockerfile_path = Column(String)
    is_input_container = Column(Boolean, default=False)
    is_output_container = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False, nullable=False)
    description = Column(String)
    filename = Column(String)

    build = relationship("ContainerBuild", backref="container", uselist=False)
    user = relationship("User", backref="container", uselist=False)
    tags = relationship("Tag", secondary="container_tags")

    @property
    def dockerfile_abs_path(self):
        return os.path.join(config.UPLOAD_DIR, self.dockerfile_path)

    @property
    def build_abs_path(self):
        return os.path.dirname(self.dockerfile_abs_path)


class ContainerBuild(TimestampMixin, Base):
    container_id = Column(ForeignKey("container.id", **CASCADE))
    exit_code = Column(Integer)
    status = Column(String)
    tag = Column(String)

    error = relationship("ContainerBuildError", uselist=False, backref="build")

    @property
    def is_success(self):
        return self.exit_code == 0

    def generate_tag(self) -> str:
        return f"{config.IMAGE_TAG_PREFIX}.{self.container.name.strip()}.{self.container.id}".replace(
            " ", ""
        )


class ContainerBuildError(Base):
    container_build_id = Column(ForeignKey("container_build.id", ondelete="CASCADE"))
    stderr = Column(String)


class Tag(Base):
    tag_name = Column(String)

    containers = relationship("Container", secondary="container_tags")
