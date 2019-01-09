import asyncio
import ujson
from prodict import Prodict as pdict
from itertools import count
from copy import deepcopy

from band import logger, settings, rpc, app, scheduler
from band.constants import (
    NOTIFY_ALIVE, REQUEST_STATUS, OK, FRONTIER_SERVICE,
    DIRECTOR_SERVICE)

from ..helpers import nn, merge_dicts
from ..band_config import BandConfig
from ..constants import (
    STARTED_SET, SERVICE_TIMEOUT, DEFAULT_COL, DEFAULT_ROW,
    STATUS_RESTARTING, STATUS_REMOVING, STATUS_STARTING,
    STATUS_STOPPING, SHARED_CONFIG_KEY)

from ..docker_manager import DockerManager
from .context import StateCtx
from .service import ServiceState
from ..image_navigator import ImageNavigator
from .grid import is_valid_pos, ServicesGrid

image_navigator = ImageNavigator(**settings)
band_config = BandConfig(**settings)
dock = DockerManager(image_navigator=image_navigator, **settings)


class StateManager:
    def __init__(self):
        self.timeout = 30
        self._state = dict()
        self._shared_config = dict()
        self.registrations_hash = ''
        self.grid = ServicesGrid(self)

    """
    Lifecycle functions
    """

    async def initialize(self):
        await band_config.initialize()
        await image_navigator.load()
        await self.load_config(SHARED_CONFIG_KEY)
        await self.resolve_docstatus_all()
        await dock.initialize()

        # initial fill autostart 
        started_present = await band_config.set_exists(STARTED_SET)
        if not started_present:
            await band_config.set_add(STARTED_SET, *settings.initial_startup)

        # looking for containers to request status
        for container in await dock.containers(struct=list):
            if container.running and container.native:
                await scheduler.spawn(
                    self.request_app_state(container.name))
        
        # spawning state cleaner job
        await scheduler.spawn(self.clean_worker())

        await scheduler.spawn(self.images_loader())

        # handling autostart
        await self.handle_auto_start()

    async def images_loader(self):
        while True:
            await asyncio.sleep(15)
            try:
                await image_navigator.load()
            except Exception:
                logger.exception('ex')

    async def clean_worker(self):
        while True:
            # Remove expired services
            try:
                await asyncio.sleep(5)
                await self.resolve_docstatus_all()
                await self.check_regs_changed()
            except ConnectionRefusedError:
                logger.error('Redis connection refused')
            except asyncio.CancelledError:
                logger.warn('Asyncio cancelled')
                break
            except Exception:
                logger.exception('state initialize')
            await asyncio.sleep(1)

    async def handle_auto_start(self):
        services = await self.should_start()
        logger.info("Autostarting services", items=services)
        for item in services:
            svc = await self.get(item)
            if not svc.is_active() and image_navigator.is_native(svc.name):
                await self.run_service(svc.name)
            # if not (item in state and ().is_active()):
            # asyncio.ensure_future(run(item))

    async def unload(self):
        await band_config.unload()
        await dock.close()

    """
    State functions
    """

    @property
    def state(self):
        return self._state

    def values(self):
        return self._state.values()

    def __iter__(self):
        return iter(self._state)

    def __contains__(self, name):
        return self.is_exists(name)

    def is_exists(self, name):
        return name in self._state

    """
    Container management functions
    """

    async def get(self, name, **kwargs):
        params = kwargs.pop('params', pdict())
        positions = []
        
        # Container env
        envs = []
        if params.env:
            envs.append(params.env)

        if params.get('pos') and is_valid_pos(params.pos):
            positions.append(params.pos)

        if name not in self._state:
            logger.debug('loading state', name=name)
            config = await self.load_config(name)
            meta = await image_navigator.image_meta(name)
            svc = ServiceState(name=name, manager=self)

            if config:
                if config.get('env'):
                    envs.append(config['env'])
                if config.get('pos') and is_valid_pos(config['pos']):
                    positions.append(config['pos'])

            if meta:
                svc.set_meta(meta)
                if meta.env:
                    envs.append(meta.env)
                if meta.get('pos') and is_valid_pos(meta['pos']):
                    positions.append(meta['pos'])

            positions.append(self.grid.default_pos)
            self._state[name] = svc

        svc = self._state[name]

        # env variables
        if len(envs):
            svc.set_env(merge_dicts(*envs))

        # passed build options
        if params.build_opts:
            svc.set_build_opts(**params.build_opts)

        # position allocation
        if len(positions):
            # TODO: pass list of positions
            await self.set_pos(name, positions.pop(0), svc=svc)

        return svc

    def logs_reader(self):
        return dock.get_log_reader()

    async def run_service(self, name, no_wait=False):
        svc = await self.get(name)
        svc.clean_status()
        svc.set_status_override(STATUS_STARTING)
        coro = self._do_run_service(name)
        await (scheduler.spawn(coro) if no_wait else coro)
        return svc

    async def _do_run_service(self, name):
        svc = await self.get(name)
        env = deepcopy(self._shared_config.get('env', {}))
        env.update(svc.env)
        await dock.run_container(name, env=env, **svc.build_options)
        await band_config.set_add(STARTED_SET, name)
        logger.debug('svc', svc=dict(bo=svc.build_options, e=svc.env))
        logger.debug('saving config')
        svc.save_config()
        logger.debug('resolving svc status')
        await self.resolve_docstatus(name)

    async def remove_service(self, name, no_wait=False):
        svc = await self.get(name)
        await band_config.set_rm(STARTED_SET, name)
        svc.set_status_override(STATUS_REMOVING)
        coro = self._do_remove_service(name)
        await (scheduler.spawn(coro) if no_wait else coro)
        return svc

    async def _do_remove_service(self, name):
        svc = await self.get(name)
        await dock.remove_container(name)
        svc.clean_status()

    async def stop_service(self, name, no_wait=False):
        svc = await self.get(name)
        await band_config.set_rm(STARTED_SET, name)
        svc.set_status_override(STATUS_STOPPING)
        coro = self._do_stop_service(name)
        await (scheduler.spawn(coro) if no_wait else coro)
        return svc

    async def _do_stop_service(self, name):
        svc = await self.get(name)
        await dock.stop_container(name)
        svc.clean_status()

    async def start_service(self, name, no_wait=False):
        svc = await self.get(name)
        if svc.native:
            await band_config.set_add(STARTED_SET, name)
        svc.set_status_override(STATUS_STARTING)
        coro = self._do_start_service(name)
        await (scheduler.spawn(coro) if no_wait else coro)
        return svc

    async def _do_start_service(self, name):
        svc = await self.get(name)
        await dock.start_container(name)
        svc.clean_status()

    async def restart_service(self, name, no_wait=False):
        svc = await self.get(name)
        svc.set_status_override(STATUS_RESTARTING)
        coro = self._do_restart_service(name)
        await (scheduler.spawn(coro) if no_wait else coro)
        return svc

    async def _do_restart_service(self, name):
        container = await dock.get(name)
        svc = await self.get(name)
        if container:
            svc.clean_status()
            await dock.restart_container(name)
            svc.clean_status()
            await self.check_regs_changed()

    async def set_pos(self, name, pos, svc=None):
        """
        Try to allocate serive position at dashboard
        """
        if not svc:
            svc = await self.get(name)
        if is_valid_pos(pos):
            pos = self.grid.allocate(name, col=pos.get('col'), row=pos.get('row'))
            svc.set_pos(**pos)


    """
    State functions
    """

    async def resolve_docstatus(self, name):
        svc = await self.get(name)
        container = await dock.get(name)
        if container:
            svc.set_dockstate(container.full_state())

    async def resolve_docstatus_all(self):
        for container in await dock.containers(struct=list):
            await self.resolve_docstatus(container.name)

    async def clean_status(self, name):
        (await self.get(name)).clean_status()

    async def request_app_state(self, name):
        svc = await self.get(name)
        # Service-dependent payload send with status request
        payload = dict()
        # Payload for frontend servoce
        if name == FRONTIER_SERVICE:
            payload.update(self.registrations())
            payload.update(dict(state_hash=self.registrations_hash))

        # Loading state, config, meta
        status = await rpc.request(name, REQUEST_STATUS, **payload)
        if status:
            svc.set_appstate(dict(status))

    async def check_regs_changed(self):
        new_hash = hash(str(self.registrations()))
        # If registrations changed front shold know about that
        if new_hash != self.registrations_hash:
            self.registrations_hash = new_hash
            await self.request_app_state(FRONTIER_SERVICE)

    def registrations(self):
        methods = []
        for svc in self.values():
            if svc.is_active():
                for method in svc.methods:
                    methods.append(method)
        return dict(register=methods)

    def clean_ctx(self, name, coro):
        return StateCtx(self, name, coro)

    """
    Config store functions
    """

    async def configs(self):
        return await band_config.configs_list()

    async def load_config(self, name):
        config = await band_config.load_config(name)
        if name == SHARED_CONFIG_KEY and config:
            self._shared_config = config
        logger.debug('loaded config', name=name, config=config)
        return config

    def save_config(self, name, config):
        logger.info('saving', name=name, config=config)
        job = scheduler.spawn(band_config.save_config(name, config))
        asyncio.ensure_future(job)

    async def runned_set(self):
        return await band_config.set_get(STARTED_SET)

    async def update_config(self, name, keysvals):
        config = (await self.load_config(name)) or pdict()
        for k, v in keysvals.items():
            target = config
            path = k.split('.')
            prop = path.pop()
            for p in path:
                target = target[p]
            if v == '':
                target.pop(prop, None)
            else:
                target[prop] = v
        self.save_config(name, config)
        if name == SHARED_CONFIG_KEY:
            self._shared_config = config
        return config

    async def should_start(self):
        return await band_config.set_get(STARTED_SET)
