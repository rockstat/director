FMT_JSON = ' FORMAT JSON'
FMT_JSON_ROW = ' FORMAT JSONEachRow'

def events_where():
    return """
        date BETWEEN today() -1 AND today()
        AND timestamp > (toUInt64(now() - ((60 * 60) * 24)) * 1000)
    """


def groups(where):
    return """
        SELECT
            'sources' as group,
            sess_type as param,
            uniq(uid) AS v
        FROM events
        WHERE
            events.name = 'session'
            AND {where}
        GROUP BY param
        ORDER BY v desc

    UNION ALL

        SELECT
            'newusers' as group,
            if(sess_num == 1, 'new users', 'returning users') as param,
            uniq(uid) AS v
        FROM events
        WHERE
            events.name = 'session'
            AND {where}
        GROUP BY param
        ORDER BY v desc

    UNION ALL

        SELECT
            'devices' as group,            
            CASE
                WHEN uaparser_is_mob == 1 THEN 'smartphone'
                WHEN uaparser_is_tablet == 1  THEN 'tablet'
                WHEN uaparser_is_pc == 1  THEN 'desktop'
                ELSE 'other'
            END as param,
            uniq(uid) AS v
        FROM events
        WHERE
            events.name = 'session'
            AND {where}
        GROUP BY param, uaparser_is_mob, uaparser_is_tablet, uaparser_is_pc
        ORDER BY v desc

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
