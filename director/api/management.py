import asyncio
from prodict import Prodict as pdict
from typing import List, Dict
from band import settings, rpc, logger, expose
from band.constants import (NOTIFY_ALIVE, REQUEST_STATUS, OK, FRONTIER_SERVICE,
                            DIRECTOR_SERVICE)
from band.lib.response import BaseBandResponse
from ..constants import (STATUS_RUNNING, STARTED_SET, SHARED_CONFIG_KEY)
from ..structs import RunParams, BuildOptions, ServicePostion
from ..helpers import merge, req_to_bool
from .. import dock, state, image_navigator
"""
Request helpers
"""


def build_options_from_req(params: Dict):
    """
    Build BuildOptions from request params
    """
    return BuildOptions(
        nocache=req_to_bool(params.get('nocache', None)),
        auto_remove=req_to_bool(params.get('auto_remove', None)),
        env=pdict.from_dict(params.get('env', {})))


"""
Band ecosystem methods
"""


@expose(path='/list')
async def states_list():
    return list(svc.full_state() for svc in state.values()
                if svc.is_active() or svc.is_local())


@expose(path='/state')
async def get_state(name=None, prop=None):
    """
    Get list of services in state or get state of specified service
    Method for debug purposes
    """
    if name:
        if name in state:
            srv = await state.get(name)
            if prop and hasattr(srv, prop):
                return getattr(srv, prop)
            return srv.full_state()
    return list(state.state.keys())


@expose(path='/show/{name}')
async def show(name, **params):
    """
    Returns container details
    """
    container = await dock.get(name)
    if not container:
        return 404
    return container and container.full_state()


@expose()
async def registrations(**params):
    """
    Provide global RPC registrations information
    Method for debug purposes
    """
    return state.registrations()


@expose(name=NOTIFY_ALIVE)
async def status_receiver(name, **params):
    """
    Listen for services promotions then ask their statuses.
    It some cases takes payload to reduce calls amount
    """
    await state.request_app_state(name)


@expose(path='/ask_state/{name}')
async def ask_state(name, **params):
    """
    Ask service state
    """
    return await rpc.request(name, REQUEST_STATUS)


@expose(path='/call/{name}/{method}')
async def call(name, method, **params):
    """
    Call service method
    Use timeout__ param to set RPC response timeout
    """
    logger.info(f'Calling method "{method}" with params "{params}"')
    res = await rpc.request(name, method, **params)
    if isinstance(res, BaseBandResponse):
        res = res._asdict()
    return res


"""
Images methods
"""


@expose()
async def list_images(**params):
    """
    Available images list
    """
    return await image_navigator.lst()


"""
Containers management
"""


@expose(path='/run/{name}')
async def run(name, **req_params):
    """
    Create image and run new container with service
    params:
    pos - string contains prefered coordinates, for example "2x3" (col x row)
    nocache - 
    auto_remove -
    env - 
    """

    if not image_navigator.is_native(name):
        return 404

    logger.debug('Called api.run with', params=req_params)
    params = RunParams(
        pos=ServicePostion.from_string(req_params.get('pos')),
        build_opts=build_options_from_req(req_params))

    svc = await state.get(name, params=params)
    logger.info('request with params', params=params, srv_config=svc.config)

    svc = await state.run_service(name, no_wait=True)
    return svc.full_state()


@expose(path='/set_pos/{name}')
async def set_pos(name, **params):
    """
    Set container position
    """
    # check container exists
    if not state.is_exists(name):
        return 404
    
    pos = ServicePostion.from_string(params.get('pos'))
    await state.set_pos(name, pos)
    
    svc = await state.get(name)
    return svc.full_state()


@expose()
async def rebuild_all(**kwargs):
    """
    Rebuild all controlled containers
    """
    for name in await state.should_start():
        await run(name)
    return 200


@expose(path='/restart/{name}')
async def restart(name, **params):
    """
    Restart service
    """
    svc = await state.restart_service(name, no_wait=True)
    return svc.full_state()


@expose(path='/stop/{name}')
async def stop(name, **params):
    """
    Stop container. Only for persistent containers
    """
    # check container exists
    if not state.is_exists(name):
        return 404
    # executing main action
    svc = await state.stop_service(name, no_wait=True)
    return svc.full_state()


@expose(path='/start/{name}')
async def start(name, **params):
    """
    Start
    """
    if not state.is_exists(name):
        return 404
    # executing main action
    svc = await state.start_service(name, no_wait=True)
    return svc.full_state()


@expose(path='/rm/{name}')
async def remove(name, **params):
    """
    Unload/remove service
    """
    # check container exists
    if not state.is_exists(name):
        return 404
    svc = await state.remove_service(name, no_wait=True)
    return svc.full_state()


"""
Services configuration
"""


@expose()
async def configs_list(**params):
    """
    List of saved services configurations
    """
    return await state.configs()


@expose(path='/update_config/{name}')
async def update_config(name, **params):
    """
    Updates service configuration.
    To remove parameter send it with empty value
    Supported dot notation for example env.TESTVAR=213
    """
    return await state.update_config(name, params)


@expose(path='/get_config/{name}')
async def get_config(name, **params):
    """
    Returns service config
    """
    return await state.load_config(name)
