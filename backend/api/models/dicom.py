import os

from sqlalchemy import *
from sqlalchemy.orm import relationship

from api import config
from . import Base, PathMixin, NestedPathMixin, CASCADE


class DicomNode(PathMixin, Base):
    title = Column(String)
    host = Column(String)
    port = Column(Integer)
    input = Column(Boolean, default=False)
    output = Column(Boolean, default=False)

    implementation_version_name = Column(String)
    first_connected = Column(DateTime)
    last_connected = Column(DateTime)

    # Null user ID means DicomNode is available globally
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    patients = relationship("DicomPatient", backref="node")
    user = relationship("User", backref="dicom_nodes")

    __table_args__ = (
        UniqueConstraint("title", "host", "port", "user_id", name="_node_uc"),
    )

    def __eq__(self, other) -> bool:
        return (
            self.host == other.host
            and self.port == other.port
            and self.title == other.title
        )

    @property
    def is_rts(self):
        return self.host == config._RTS_HOST and self.port == config._RTS_PORT


class DicomPatient(NestedPathMixin, Base):
    dicom_node_id = Column(Integer, ForeignKey("dicom_node.id", **CASCADE))
    patient_id = Column(String)

    studies = relationship("DicomStudy", backref="patient")

    def get_path(self) -> str:
        return os.path.join(self.node.get_path(), str(self.id))


class DicomStudy(NestedPathMixin, Base):
    dicom_patient_id = Column(Integer, ForeignKey("dicom_patient.id", **CASCADE))
    study_instance_uid = Column(String)
    study_date = Column(DateTime)

    series = relationship("DicomSeries", backref="study")

    def get_path(self) -> str:
        return os.path.join(self.patient.get_path(), str(self.id))


class DicomSeries(NestedPathMixin, Base):
    dicom_study_id = Column(Integer, ForeignKey("dicom_study.id", **CASCADE))
    series_instance_uid = Column(String)
    series_description = Column(String)
    modality = Column(String)
    date_received = Column(DateTime)

    def get_path(self) -> str:
        return os.path.join(self.study.get_path(), str(self.id))
