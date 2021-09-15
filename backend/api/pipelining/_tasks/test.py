import time
from . import dramatiq, external_sio


@dramatiq.actor
def run_test_task():
    print("[Start] Test Task")
    external_sio.emit("message", f"Running A test task")
    external_sio.emit("message", f"Finished A test task")
    print("[Finished] Test Task")
