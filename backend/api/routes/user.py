from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api import session
from api.auth import admin_auth
from api.auth import token_auth
from api.models.user import User, UserLocal
from api.schemas.user import (
    User as UserSchema,
    UserLocalCreate,
    UserEdit,
    PermittedApplicationEntities,
    ApplicationEntity,
)

router = APIRouter()


@router.get("/", response_model=List[UserSchema], dependencies=[Depends(admin_auth)])
def get_all_users(db: Session = Depends(session)):
    """Gets all the users in the database. Only Admins are allowed to access this endpoint."""

    return db.query(User).all()


@router.post("/", response_model=UserSchema)
def create_local_user(user_schema: UserLocalCreate, db: Session = Depends(session)):
    """Allows the creation of a local user."""

    try:
        user = User(username=user_schema.username, name=user_schema.name)
        user.access_allowed = True
        user.save(db)

        UserLocal(id=user.id, password=user_schema.password).save(db)

    except IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")
    else:
        return user


@router.get("/me", response_model=UserSchema)
def get_the_current_user(user: User = Depends(token_auth)):
    """Get current user"""
    return user


@router.put("/{user_id}", response_model=UserSchema)
def edit_user_settings(
    user_id: int,
    new_info: UserEdit,
    user: User = Depends(token_auth),
    db: Session = Depends(session),
):
    """Edit user settings"""
    if user.id != user_id and not user.is_admin:
        return HTTPException(403, "Unauthorized")

    if not (user_to_edit := db.query(User).get(user_id)):
        return HTTPException(401, "User does not exist")

    user_to_edit.ae_title = new_info.ae_title

    if user.is_admin:
        user_to_edit.access_allowed = new_info.access_allowed
        user_to_edit.is_admin = new_info.is_admin

    user_to_edit.save(db)
    return user_to_edit
