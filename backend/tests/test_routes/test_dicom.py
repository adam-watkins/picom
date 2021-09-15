from sqlalchemy.orm.session import Session
from tests import client, utils
from api.models.dicom import DicomNode


def test_get_user_dicom_nodes(db, authorization_header):
    # Delete existing DICOM nodes in db
    db.query(DicomNode).delete()
    db.commit()

    current_user = utils.get_test_user(db)
    other_user = utils.create_local_user("other", "other", "other")

    # Create DICOM
    global_node = save_node_for_user_id(None, db)
    user_node = save_node_for_user_id(current_user.id, db)
    db.commit()

    response = client.get(f"/dicom/nodes", headers=authorization_header)
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 2
    for node in data:
        assert node["user_id"] in [global_node.user_id, user_node.user_id]


def save_node_for_user_id(user_id: int, db: Session):
    node = DicomNode(title="test", host="test", port="0000", user_id=user_id)
    node.save(db)
    return node
