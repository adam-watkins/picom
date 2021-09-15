import os
import shutil
from typing import List

from fastapi import APIRouter, Depends

from api import config

router = APIRouter()


@router.get("")
def get_application_settings():
    """Returns user safe configuration settings for the application"""

    return config.to_json()
