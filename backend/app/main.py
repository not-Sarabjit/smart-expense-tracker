from fastapi import FastAPI

from app.core.logging import setup_logging
import logging

from passlib.context import CryptContext


## Main setup for logging
setup_logging()

# Creating a logger for this module
logger = logging.getLogger(__name__)


app = FastAPI()


@app.get('/health')
def get_health():
    return {'status' : 'OK'}