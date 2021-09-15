from api import config
from api.models.user import User
from api.models.container import Container
from api.models.dicom import DicomNode
from api.queries import internal


def pre_populate_internal(db):
    """Adds a default internal user and default containers if they do not exist"""

    if not (user := internal.get_internal_user(db)):
        user = User(username=config.INTERNAL_USERNAME, name=config.INTERNAL_USERNAME)
        user.save(db)

    if not internal.get_default_containers(db):
        [
            Container(user_id=user.id, is_shared=True, **kwargs).save(db)
            for kwargs in config.DEFAULT_CONTAINERS
        ]

    if not internal.get_return_to_sender(db):
        DicomNode(
            title="Dynamic", host="*", port=-1, output=True, user_id=user.id
        ).save(db)
