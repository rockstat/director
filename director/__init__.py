import band
from band import settings, logger, app, worker, unloader

from .state import *
from .constants import *

state = StateManager()

# Required state
from .api import stat_api, manager_api
from .queries import *

@worker()
async def __state_up():
    await state.initialize()

@unloader()
async def __state_down():
    await state.unload()

__VERSION__ = '0.3.0'

