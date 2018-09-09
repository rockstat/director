import asyncio
import ujson
from band import ClickHouse, expose, logger, settings
from .. import stat_queries

ch = ClickHouse()


@expose()
async def common_stat(**params):
    where = stat_queries.events_where()
    stat_groups = await ch.select(stat_queries.groups(where) + stat_queries.FMT_JSON)
    if stat_groups:
        return ujson.loads(stat_groups)['data']
    return {}


@expose()
async def events_stat(**params):
    events_where = stat_queries.events_where()
    stat_events = await ch.select(stat_queries.events(events_where) + stat_queries.FMT_JSON)
    return ujson.loads(stat_events)['data'] if stat_events else []
