from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api import session, config
from api.auth.ldap import LDAPManager
from api.models.user import User
from api.schemas.user import Token

router = APIRouter()
ldap = LDAPManager()


class LoginException(HTTPException):
    def __init__(
        self, status_code=401, detail="Incorrect username or password", **kwargs
    ):
        super().__init__(status_code, detail, **kwargs)


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(session)
):
    username = form_data.username
    password = form_data.password
    user = User.query(db).filter_by(username=username).first()

    # Try creating an new ldap account
    if not user and config.LDAP_AUTH_ENABLED:
        user = ldap.user_factory(username, password, db)

    # User is invalid
    if not user:
        raise LoginException()

    # Try LDAP authentication
    if user.ldap_user and not ldap.authenticate(username, password):
        raise LoginException()

    # Local user Authentication
    elif user.local_user and not user.local_user.verify_password(password):
        raise LoginException()

    return Token(access_token=user.generate_token())
