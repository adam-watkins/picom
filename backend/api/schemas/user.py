from typing import Optional, List
from datetime import datetime

from . import BaseORMModel, BaseModel
from .dicom import DicomNode


class UserLocalCreate(BaseModel):
    username: str
    name: str
    password: str

    class Config:
        schema_extra = {
            "example": {
                "username": "testuser",
                "name": "Mr. Testing",
                "password": "password",
            }
        }


class UserLDAPSchema(BaseORMModel):
    title: str
    department: str
    company: str


class User(BaseORMModel):
    username: str
    name: str
    is_admin: bool
    ae_title: Optional[str]
    first_seen: datetime
    last_seen: datetime
    access_allowed: bool
    ldap_user: Optional[UserLDAPSchema]


class UserEdit(BaseModel):
    ae_title: Optional[str]
    access_allowed: bool
    is_admin: bool


class PermittedApplicationEntities(BaseModel):
    destinations: Optional[List[DicomNode]]


class ApplicationEntity(BaseORMModel):
    destination: DicomNode


class Token(BaseModel):
    access_token: str
    token_type: str = "Bearer"
