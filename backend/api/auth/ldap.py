from typing import Optional
from datetime import datetime

from ldap3 import Server, Connection, Reader, ObjectDef

from api import config
from api.models.user import User, UserLDAP


class LDAPManager:
    def __init__(self):
        self.server = Server(config.LDAP_HOST, config.LDAP_PORT)
        self.user_base = config.LDAP_USERNAME_BASE
        self.base_dn = config.LDAP_BASE_DN

        if config.LDAP_AUTH_ENABLED:
            assert Connection(self.server, auto_bind=True)

    def _get_connection(self, username, password) -> Connection:
        cn = self.user_base + username
        return Connection(self.server, cn, password)

    def authenticate(self, username: str, password: str) -> bool:
        return self._get_connection(username, password).bind()

    def user_factory(self, username: str, password: str, db) -> Optional[User]:
        connection = self._get_connection(username, password)

        # Attempting auth
        if not connection.bind():
            return None

        search_filter = config.LDAP_SEARCH_FILTER
        connection.search(self.base_dn, (search_filter % username))

        user_dn = connection.response[0]["dn"]
        user_obj = ObjectDef("user", connection)

        reader = Reader(connection, user_obj, user_dn)
        reader.search()

        result = reader.entries[0]

        # Saving user to db
        user = User(username=username, name=str(result.name))
        user.save(db)

        UserLDAP(
            id=user.id,
            title=str(result.title),
            department=str(result.department),
            company=str(result.company),
        ).save(db)

        return user
