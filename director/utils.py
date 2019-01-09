import datetime


ROCKSTAT_EPOCH = 1514764800000

def snowflake_time(id):
    """Returns the creation date in UTC of a discord id."""
    return datetime.datetime.utcfromtimestamp(((int(id) >> 22) + ROCKSTAT_EPOCH) / 1000)

def time_snowflake(datetime_obj, high=False):
    """Returns a numeric snowflake pretending to be created at the given date.
    When using as the lower end of a range, use time_snowflake(high=False) - 1 to be inclusive, high=True to be exclusive
    When using as the higher end of a range, use time_snowflake(high=True) + 1 to be inclusive, high=False to be exclusive
    Parameters
    -----------
    datetime_obj
        A timezone-naive datetime object representing UTC time.
    high
        Whether or not to set the lower 22 bit to high or low.
    """
    unix_seconds = (datetime_obj - type(datetime_obj)(1970, 1, 1)).total_seconds()
    discord_millis = int(unix_seconds * 1000 - ROCKSTAT_EPOCH)

    return (discord_millis << 22) + (2**22-1 if high else 0)
