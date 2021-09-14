from functools import wraps
from fastapi import HTTPException


def exists_or_404(func):
    """Raises a 404 exception if an object is not found"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not (ret := func(*args, **kwargs)):
            raise HTTPException(404, "Item not found")
        return ret

    return wrapper
