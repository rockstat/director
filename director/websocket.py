import aiohttp
import asyncio
import time
import ujson
from aiohttp import web
from band import dome, scheduler, logger, worker, rpc
from . import state
from concurrent.futures import CancelledError
import datetime
from simplech import AsyncClickHouse
from .structs import LogRecord

ch = AsyncClickHouse()


async def ws_sender(ws):
    subscription = state.logs_reader()
    while True:
        try:
            msg = await subscription.get()
            if msg is None:
                break

            tstr = datetime.datetime.utcfromtimestamp(
                msg.ts / 1000).strftime("%m%d %H:%m:%S.%s")[:18]
            data = {
                'id': msg.id,
                'cid': msg.cid,
                'cname': msg.name,
                'time': tstr,
                'ts': msg.ts,
                'source': msg.source,
                'data': msg.message
            }
            await ws.send_str(ujson.dumps(data))
            await rpc.notify('logs', 'write', msg=msg)
        except CancelledError:
            logger.debug('ws writer closed')
            break
        except Exception:
            logger.exception('ex')
            break


async def websocket_handler(request):
    ws = web.WebSocketResponse()

    try:
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
                print(
                    'ws connection closed with exception %s' % ws.exception())
        print('websocket connection closed')

    except CancelledError:
        logger.info('CancelledError fetched')

    except Exception:
        logger.exception('ex')
    finally:
        await sender.close()

    return ws

# Registering route
dome.routes.append(web.RouteDef('GET', '/ws', websocket_handler, kwargs={}))
