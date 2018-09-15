import band
from band import settings, logger, app, worker, cleanup

from .state import *
from .constants import *

state = StateManager()

# Required state
from .queries import *
from .api import stat_api, manager_api

@worker()
async def __state_up():
    logger.debug('Director startup worker started')
    await state.initialize()

@cleanup()
async def __state_down():
    logger.debug('Director shutdown worker started')
    await state.unload()

__VERSION__ = '0.4.1'

