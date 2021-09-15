import socketio

mgr = socketio.AsyncAioPikaManager()
sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins=[], client_manager=mgr
)
sio_app = socketio.ASGIApp(sio)

from . import index
