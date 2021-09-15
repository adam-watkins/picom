import logging

logger = logging.getLogger("uvicorn.error")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import BaseConfig

config = BaseConfig()

from .database import session, worker_session, engine
from . import models, schemas, sockets

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Raiven API", docs_url="/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.CORS_ALLOW_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ws", sockets.sio_app)

from . import middleware, routes, pipelining, scripts


@app.on_event("startup")
def startup_event():
    scripts.run_startup_scripts()
