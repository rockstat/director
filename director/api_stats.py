import asyncio
import ujson
from itertools import groupby
from band import ClickHouse, expose, logger, settings
from band.constants import RESULT_INTERNAL_ERROR, RESULT_NOT_LOADED_YET
from . import api_stats_queries as queries

ch = ClickHouse()


@expose()
async def web_categories(**params):
    result = dict(events=[], groups={})
    where = queries.events_where()
    stat_groups = await ch.select(queries.groups(where) + queries.FMT_JSON)

    if stat_groups:
        stat_groups = ujson.loads(stat_groups)['data']
        result['groups'] = {k: list(g) for k, g in groupby(
            stat_groups, lambda x: x['group'])}
    events_where = queries.events_where()
    stat_events = await ch.select(queries.events(events_where) + queries.FMT_JSON)

    if stat_events:
        result['events'] = ujson.loads(stat_events)['data']

    return result
