FMT_JSON = ' FORMAT JSON'
FMT_JSON_ROW = ' FORMAT JSONEachRow'

def events_where():
    return """
        date >= today() -1
        AND timestamp > toUInt64(now() - 86400) * 1000
    """


def groups(where):
    return """
    SELECT param as name, groupArray((n, v)) as data FROM (
        SELECT
            'sources' as param,
            sess_type as n,
            uniq(uid) AS v
        FROM events
        WHERE
            events.name = 'session'
            AND {where}
        GROUP BY n
        ORDER BY v desc

    UNION ALL

        SELECT
            'newusers' as param,
            if(sess_num == 1, 'new users', 'returning users') as n,
            uniq(uid) AS v
        FROM events
        WHERE
            events.name = 'session'
            AND {where}
        GROUP BY n
        ORDER BY v desc

    UNION ALL

        SELECT
            'devices' as param,            
            CASE
                WHEN uaparser_is_mob == 1 THEN 'smartphone'
                WHEN uaparser_is_tablet == 1  THEN 'tablet'
                WHEN uaparser_is_pc == 1  THEN 'desktop'
                ELSE 'other'
            END as n,
            uniq(uid) AS v
        FROM events
        WHERE
            events.name = 'session'
            AND {where}
        GROUP BY n, uaparser_is_mob, uaparser_is_tablet, uaparser_is_pc
        ORDER BY v desc
    )
    GROUP BY param
    """.format(where=where)


def events(where, step=900):
    return f"""
        SELECT name, groupArray((t, v)) as data FROM (
            SELECT
                events.name,
                intDiv(toUInt32(dateTime), {step}) * {step} as t,
                count() AS v
            FROM events
            WHERE
                {where}
            GROUP BY events.name, t
            ORDER BY t
        )
        GROUP BY name
        ORDER BY length(data) DESC
    """
