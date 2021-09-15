from datetime import datetime

from api.models.dicom import DicomNode
from api.services._base import DatabaseService


class DicomNodeService(DatabaseService):
    def get_from_connection(self, title, host, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return (
            DicomNode.query(self._db)
            .filter_by(title=title, host=host, **kwargs)
            .first()
        )

    def update_or_create_from_connection(
        self, title, host, user_id: int = None, **kwargs
    ) -> DicomNode:
        if node := self.get_from_connection(title, host, user_id=user_id):
            node.last_connected = datetime.utcnow()
        else:
            node = DicomNode(
                **kwargs,
                title=title,
                host=host,
                first_connected=datetime.utcnow(),
                last_connected=datetime.utcnow(),
            ).save(self._db)

        return node
