import uvicorn

from api import config, app as application
from api.dicom.scp import SCP


def start_dicom_server():
    # TODO: Move to a seperate container.
    scp_server = SCP(ae_title=config.SCP_AE_TITLE, host=config.SCP_HOST, port=config.SCP_PORT, debug=config.SCP_DEBUG)
    scp_server.start_server(blocking=False)


if __name__ == '__main__':
    if not config.RAIVEN_WORKER:
        start_dicom_server()

    uvicorn.run(
        'asgi:application',
        host=config.APT_HOST,
        port=config.API_PORT,
        reload=config.API_HOT_RELOAD
    )
