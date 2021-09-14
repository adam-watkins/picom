from api.auth import socket_auth
from . import sio


@sio.event
async def connect(sid, environ):
    user_id = None

    # TODO: Replace with a regex
    for key_value in environ["HTTP_COOKIE"].replace(" ", "").split(";"):
        key, value = key_value.split("=")

        if key == "auth._token.local":
            user_id = socket_auth(value[9:])
            break

    # Failed to authenticate
    if not user_id:
        return False

    await sio.save_session(sid, {"user_id": user_id})
    print("[Connected] User", user_id)


@sio.event
def message(sid, data):
    print("message ", data)
    return "OK", "Hello from flask"


@sio.event
def disconnect(sid):
    print("disconnect ", sid)
