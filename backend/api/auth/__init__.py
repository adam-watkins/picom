from datetime import datetime

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from api import session
from api.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# noinspection PyUnboundLocalVariable
def token_auth(
    token: str = Depends(oauth2_scheme), db: type(session) = Depends(session)
):
    if not (user_id := User.verify_token(token)) or not (
        user := User.query(db).get(user_id)
    ):
        raise HTTPException(401, "Invalid token")

    if not user.access_allowed:
        raise HTTPException(403, "User has not been approved to access Raiven")

    user.last_seen = datetime.utcnow()
    user.save(db)
    return user


def admin_auth(
    token: str = Depends(oauth2_scheme), db: type(session) = Depends(session)
):
    """Only allows users you are admins"""

    if (user := token_auth(token, db)).is_admin:
        return user

    raise HTTPException(401, "Unauthorized")


def socket_auth(token):
    """Returns the user id"""
    return User.verify_token(token)
