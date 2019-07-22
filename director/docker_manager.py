"""
Rockstat Director docker module

Useful links:
https://ahmet.im/blog/docker-logs-api-binary-format-explained/
http://aiodocker.readthedocs.io/en/latest/
https://docs.docker.com/engine/api/v1.37/#operation/ContainerList
https://docs.docker.com/engine/api/v1.24/#31-containers
"""
from pathlib import Path
from collections import namedtuple
import aiofiles
import os
import sys
import stat
import struct
import re
import asyncio
import aiodocker
import ujson
import subprocess
from aiodocker.exceptions import DockerError
from aiodocker.logs import DockerLog
from aiodocker.channel import Channel, ChannelSubscriber
from aiodocker.containers import DockerContainer
from prodict import Prodict as pdict
from time import time
from typing import Set, List, Dict
from pprint import pprint

from band import logger, scheduler, loop
from .image_navigator import ImageNavigator
from .band_container import BandContainer, BandContainerBuilder
from .constants import DEF_LABELS, STATUS_RUNNING
from .helpers import req_to_bool, def_val
from .flake import Flake
from .structs import LogRecord
from base64 import b64encode

idgen = Flake()
logs_sources = {
    '1': 'stdin',
    '2': 'stderr'
}

class DockerManager():
    image_navigator: ImageNavigator
    reserved_ports: Set
    container_params: pdict

    def __init__(self,
                 images,
                 container_params,
                 image_params,
                 image_navigator,
                 start_port=8900,
                 end_port=8999,
                 **kwargs):
        # instance of low-level async docker client
        self.dc = aiodocker.Docker()
        # containers images navigator
        self.image_navigator = image_navigator
        # pool start port
        self.start_port = start_port
        # pool end port
        self.end_port = end_port
        # ports reservation
        self.reserved_ports = set()
        # common container params
        self.container_params = pdict.from_dict(container_params)
        self.image_params = pdict.from_dict(image_params)

    async def initialize(self):
        self.logs = Channel()
        await scheduler.spawn(
            self.events_reader(self.dc, self.logs))

    async def logs_reader(self, docker, container: DockerContainer, channel: Channel, name, cid):
        log_reader = container.logs
        subscriber = log_reader.subscribe()
        unixts = int(time())
        
        await scheduler.spawn(log_reader.run(since=unixts))
        while True:
            log_record = await subscriber.get()
            ts, id = idgen.take()
            if log_record is None:
                logger.info('closing docker logs reader')
                break
            mv = memoryview(log_record)
            if len(log_record) <= 8:
                logger.warn('small shit', len=len(log_record), b64val=b64encode(log_record).decode())
                continue
            message = bytes(mv[8:]).decode('utf-8', 'replace')
            source = logs_sources.get(str(mv[0]), '')
            size = struct.unpack('>L', mv[4:8])[0]
            
            msg = LogRecord(id, ts, cid, name, source, size, message)
            await channel.publish(msg)

    async def events_reader(self, docker, logs):
        subscriber = docker.events.subscribe()

        for bc in await self.containers(inband=False, status='running'):
            container = bc.container
            await scheduler.spawn(self.logs_reader(docker, container, logs, bc.name, bc.id))
            logger.debug(f'creating logger for {bc.name}')

        """
[00]             'Labels': {'band.base-py.version': '0.20.6',
[00]                        'band.service.def_position': '2x2',
[00]                        'band.service.title': 'MaxMind ip2geo',
[00]                        'band.service.version': '0.4.0',
[00]                        'inband': 'native',
[00]                        'maintainer': 'Dmitry Rodin <madiedinro@gmail.com>'},


[00] {'Action': 'start',
[00]  'Actor': {'Attributes': {'band.base-py.version': '0.20.6',
[00]                           'band.service.def_position': '2x2',
[00]                           'band.service.title': 'MaxMind ip2geo',
[00]                           'band.service.version': '0.4.0',
[00]                           'image': 'sha256:02c07a3ebb63e704b66188079c12a2b92d6ec840f135479a42b4fc198d642a2d',
[00]                           'maintainer': 'Dmitry Rodin <madiedinro@gmail.com>',
[00]                           'name': 'gracious_rubin'},
[00]            'ID': '0d2e755fca15b252a6f66d1a96b6502c12399d430e1b42cb16df6394fa0fd580'},
[00]  'Type': 'container',
[00]  'from': 'sha256:02c07a3ebb63e704b66188079c12a2b92d6ec840f135479a42b4fc198d642a2d',
[00]  'id': '0d2e755fca15b252a6f66d1a96b6502c12399d430e1b42cb16df6394fa0fd580',
[00]  'scope': 'local',
[00]  'status': 'start',
[00]  'time': datetime.datetime(2019, 7, 22, 4, 42, 17),
[00]  'timeNano': 1563759737944087100}



[00] {'Action': 'start',
[00]  'Actor': {'Attributes': {'band.base-py.version': '0.20.6',
[00]                           'band.service.def_position': '2x2',
[00]                           'band.service.title': 'MaxMind ip2geo',
[00]                           'band.service.version': '0.4.0',
[00]                           'image': 'sha256:5d64fb3ec2eaf97ab0608fb9a14f97d5745258e7daecb07f17279a686d3991e1',
[00]                           'inband': 'native',
[00]                           'maintainer': 'Dmitry Rodin <madiedinro@gmail.com>',
[00]                           'name': 'mmgeo'},
[00]            'ID': '23cf76b129a894299f3e5c4b30f2cbd06aec52fc6dcb1ac6fd4943e000a1721d'},
[00]  'Type': 'container',
[00]  'from': 'sha256:5d64fb3ec2eaf97ab0608fb9a14f97d5745258e7daecb07f17279a686d3991e1',
[00]  'id': '23cf76b129a894299f3e5c4b30f2cbd06aec52fc6dcb1ac6fd4943e000a1721d',
[00]  'scope': 'local',
[00]  'status': 'start',
[00]  'time': datetime.datetime(2019, 7, 22, 4, 42, 26),
[00]  'timeNano': 1563759746606291500}
        """
        while True:
            event = await subscriber.get()
            if event is None:
                break
            if event['Action'] != 'start' or event['Type'] != 'container':
                continue
            # Not a band container
            if 'inband' not in event['Actor']['Attributes']:
                continue
            cid = event['Actor']['ID']
            container = await docker.containers.get(cid)
            name = event['Actor']['Attributes']['name']
            await scheduler.spawn(self.logs_reader(docker, container, logs, name, cid))

    def get_log_reader(self):
        return self.logs.subscribe()

    async def containers(self, as_dict=False, status=None, fullinfo=False, inband=True):
        filters = pdict()
        if inband:
            filters.label = ['inband']
        if status:
            filters.status = [status]
        
        containers = await self.dc.containers.list(all=True, filters=ujson.dumps(filters))
        lst = []
        for c in containers:
            bc = await BandContainer.create_with_info(c)
            lst.append(bc)
        
        return lst if not as_dict else {c.name: c for c in lst}

    async def conts_list(self):
        cs = await self.containers()
        return [c.short_info for c in cs]

    async def get(self, name):
        try:
            container = await self.dc.containers.get(name)
            if container:
                return BandContainer(container)
        except DockerError as e:
            logger.warn("Fetched exception",
                        status=e.status, message=e.message)

        # return (await self.containers()).get(name, None)

    async def available_ports(self):
        available_ports = set(range(self.start_port, self.end_port))
        conts = await self.containers(fullinfo=True)
        used_ports = set()

        for cont in conts:
            cports = cont.ports
            logger.info('container ports', cname=cont.name, cports=cports)
            if not cports:
                logger.warn('no ports',  cname=cont.name, cports=cports)
            for p in cports:
                used_ports.add(p)

        logger.info(f"ports used summary", used_ports=used_ports)
        return available_ports - used_ports - self.reserved_ports

    def hold_ports(self, ports):
        for port in ports:
            self.reserved_ports.add(port)

    def free_ports(self, ports):
        for port in ports:
            self.reserved_ports.add(port)

    async def remove_container(self, name):
        # removing if running
        try:
            container = BandContainer(await self.dc.containers.get(name))
            if container:
                await container.fill()
                if container.state == 'running':
                    container_autoremove = container.auto_removable()
                    logger.info("Stopping container")
                    await container.stop()
                    if not container_autoremove:
                        await container.delete()
                else:
                    await container.delete()
                
                await asyncio.sleep(0.5)
                # try:
                #     await container.wait(condition="removed")
                # except DockerError as e:
                #     logger.debug('Docker 404 received on wait request')
                #     if e.status != 404:
                #         raise e

        except DockerError as exc:
            if exc.status == 404:
                pass
            else:
                logger.exception('container remove exc')
        return True

    async def stop_container(self, name):
        conts = await self.containers(as_dict=True)
        if name in conts.keys():
            c = conts[name]
            logger.info(f"stopping container {c.name}")
            await c.stop()
            return True

    async def start_container(self, name):
        conts = await self.containers(as_dict=True)
        if name in conts.keys():
            c = conts[name]
            logger.info(f"starting container {c.name}")
            await c.start()
            return True

    async def restart_container(self, name):
        conts = await self.containers(as_dict=True)
        if name in conts.keys():
            c = conts[name]
            logger.info(f"restarting container {c.name}")
            await c.restart()
            return True

    async def create_image(self, img, img_options):
        logger.debug("Building image", n=img.name, io=img_options, path=img.path)
        async with img.create(img_options) as builder:
            progress = pdict()
            struct = builder.struct()
            last_time = time()
            async for chunk in await self.dc.images.build(**struct):
                if isinstance(chunk, dict):
                    if chunk.get('aux'):
                        struct.id = chunk.get('aux').get('ID')
                        logger.debug('chunk', chunk=chunk)
                    elif chunk.get('status') and chunk.get('id'):
                        progress[chunk.get('id')] = chunk
                        if time() - last_time > 1:
                            logger.info("\nDocker build progress", progress=progress)
                            last_time = time()
                    elif chunk.get('stream'):
                        # logger.debug('chunk', chunk=chunk)
                        step = re.search(r'Step\s(\d+)\/(\d+)', chunk.get('stream'))
                        if step:
                            logger.debug('Docker build step ', groups=step.groups())
                    else:
                        logger.debug('unknown chunk', chunk=chunk)
                else:
                    logger.debug('unknown chunk type', type=type(chunk), chunk=chunk)
            if not struct.id:
                raise Exception('Build process not completed')
            logger.info('Docker image created', struct_id=struct.id)
            return img.set_data(await self.dc.images.get(img.name))

    async def run_container(self, name, env={}, nocache=None, auto_remove=None, **kwargs):

        image_options = dict(
            nocache=def_val(nocache, False),
            **self.image_params
        )
        container_options = dict(auto_remove=def_val(auto_remove, False))

        logger.info('called run container (kwargs will not used)', env=env,
                    func_args=dict(auto_remove=auto_remove, nocache=nocache, kwargs=kwargs), image_options=image_options, container_options=container_options)

        # building image
        service_img = self.image_navigator[name]

        logger.info('Building image', name=name)
        await self.create_image(service_img, image_options)
        logger.info('Removing active container', name=name)
        
        await self.remove_container(name)
        await asyncio.sleep(0.1)
        # preparing to run
        available_ports = await self.available_ports()
        allocated_ports = list(available_ports.pop()
                               for p in service_img.ports)
        self.hold_ports(allocated_ports)
        try:
            params = pdict.from_dict({
                **dict(host_ports=allocated_ports),
                **self.container_params})
            params.env.update(env)
            builder = BandContainerBuilder(service_img)
            config = builder.run_struct(name, **container_options, **params)
            # running service
            logger.info(f"starting container {name}.")
            dc = await self.dc.containers.run(config=config, name=name)
            c = BandContainer(dc)
            await c.ensure_filled()
            logger.info(f'started container {c.name} [{c.short_id}] {c.ports}')
            return c.short_info
        except Exception as exc:
            raise exc
        finally:
            self.free_ports(allocated_ports)

    async def close(self):
        await self.dc.close()
