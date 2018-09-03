import asyncio
import ujson
from itertools import groupby
from band import ClickHouse, expose, logger, settings
from band.constants import RESULT_INTERNAL_ERROR, RESULT_NOT_LOADED_YET
from . import api_stats_queries as queries

ch = ClickHouse()


@expose()
async def common_stat(**params):
    where = queries.events_where()
    stat_groups = await ch.select(queries.groups(where) + queries.FMT_JSON)
    if stat_groups:
        return ujson.loads(stat_groups)['data']
    return {}


@expose()
async def events_stat(**params):
    events_where = queries.events_where()
    stat_events = await ch.select(queries.events(events_where) + queries.FMT_JSON)
    return ujson.loads(stat_events)['data'] if stat_events else []
