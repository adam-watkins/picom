from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer,
    BadSignature,
    SignatureExpired,
)
from passlib.hash import pbkdf2_sha256

from sqlalchemy import *
from sqlalchemy.orm import relationship, Session
from datetime import datetime

from . import Base
from api import config


class User(Base):
    __serializer__ = Serializer(config.SECRET_KEY, expires_in=config.TOKEN_TTL)

    username = Column(String, index=True, unique=True)
    name = Column(String)
    ae_title = Column(String)
    is_admin = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)
    access_allowed = Column(Boolean, default=False)

    ldap_user = relationship("UserLDAP", backref="user", uselist=False)
    local_user = relationship("UserLocal", backref="user", uselist=False)

    def generate_token(self) -> bytes:
        return self.__serializer__.dumps({"id": self.id})

    @staticmethod
    def verify_token(token) -> int:
        try:
            data = User.__serializer__.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        else:
            return data["id"]

    @classmethod
    def _set_serializer(cls, secret_key, expiration):
        cls.__serializer__ = Serializer(secret_key, expiration)


class UserLDAP(Base):
    id = Column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    title = Column(String)
    department = Column(String)
    company = Column(String)

    def verify_password(self, password):
        raise NotImplementedError


class UserLocal(Base):
    id = Column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    password = Column(String)

    def verify_password(self, password):
        return pbkdf2_sha256.verify(password, self.password)

    def save(self, *args, **kwargs):
        self.password = pbkdf2_sha256.hash(self.password)
        return super().save(*args, **kwargs)
