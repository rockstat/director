import aiohttp
import asyncio
import time
import ujson
from aiohttp import web
from band import dome, scheduler, logger, worker
from . import state
from concurrent.futures import CancelledError
from .flake import Flake
import datetime
from simplech import AsyncClickHouse

idgen = Flake()
ch = AsyncClickHouse()

@worker()
async def ch_writer():
    subscription = state.logs_reader()
    while True:
        msg = await subscription.get()
        now, cid, name, source, size, data = msg


async def ws_sender(ws):
    subscription = state.logs_reader()
    while True:
        try:
            msg = await subscription.get()
            if msg is None:
                break
            
            now, cid, name, source, size, data = msg
            tstr = datetime.datetime.now().strftime("%m%d %H:%m:%S.%s")[:18]
            data = {
                'id': idgen.take(),
                'cid': cid,
                'cname': name,
                'time': tstr,
                'ts': now,
                'source': source,
                'data': data
            }
            await ws.send_str(ujson.dumps(data))
        except CancelledError:
            logger.debug('ws writer closed')
            break
        except Exception:
            logger.exception('ex')
            break


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    sender = await scheduler.spawn(ws_sender(ws))
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                # MSG handler
                pass
                # await ws.send_str(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())
    await sender.close()
    print('websocket connection closed')

    return ws

# Registering route
dome.routes.append(web.RouteDef('GET', '/ws', websocket_handler, kwargs={})) 