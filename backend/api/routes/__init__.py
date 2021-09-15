from fastapi import Depends

from api import app, session, schemas
from api.auth import token_auth

from . import (
    application_entity,
    pipeline,
    container,
    user,
    dicom,
    auth,
    test,
    settings,
    vfs,
)

# Auth Routes
app.include_router(test.router, tags=["Test"], prefix="/test")
app.include_router(auth.router, tags=["Auth"], prefix="/auth")

# All Secure Except for create_local_user
app.include_router(user.router, tags=["User"], prefix="/user")

# Secure Routes
secure_deps = [Depends(token_auth)]

app.include_router(
    application_entity.router,
    tags=["Application Entity"],
    prefix="/ae",
    dependencies=secure_deps,
)
app.include_router(
    pipeline.router, tags=["Pipeline"], prefix="/pipeline", dependencies=secure_deps
)
app.include_router(
    container.router, tags=["Container"], prefix="/container", dependencies=secure_deps
)
app.include_router(
    dicom.router, tags=["Dicom"], prefix="/dicom", dependencies=secure_deps
)
app.include_router(
    settings.router, tags=["Settings"], prefix="/settings", dependencies=secure_deps
)
app.include_router(
    vfs.router, tags=["Virtual File System"], prefix="/vfs", dependencies=secure_deps
)
