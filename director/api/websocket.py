import aiohttp
from aiohttp import web
from band import dome

# async def websocket_handler(request):

#     ws = web.WebSocketResponse()
#     await ws.prepare(request)

#     async for msg in ws:
#         if msg.type == aiohttp.WSMsgType.TEXT:
#             if msg.data == 'close':
#                 await ws.close()
#             else:
#                 await ws.send_str(msg.data + '/answer')
#         elif msg.type == aiohttp.WSMsgType.ERROR:
#             print('ws connection closed with exception %s' %
#                   ws.exception())

#     print('websocket connection closed')

#     return ws


# dome.routes.append(web.RouteDef('GET', '/ws', websocket_handler, kwargs={})) 