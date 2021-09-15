from typing import List

from fastapi import APIRouter

from api import pipelining


router = APIRouter()


@router.get("/")
def run_test_task():
    pipelining.run_test_task()

    return "Running Test"
