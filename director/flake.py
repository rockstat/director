import asyncio
import time
import math

ROCKSTAT_EPOCH = 1514764800000
TIME_SHIFT = 24


class Flake:
    def __init__(self):
        self.offset = 0
        self.counter = 0
        self.last_ts = 0


    def take(self):
        t1 = int(time.time() * 1000)
        if t1 > self.last_ts:
            self.last_ts = t1
            self.counter = 0
            self.offset = (t1 - ROCKSTAT_EPOCH) << TIME_SHIFT
        self.counter += 1
        return (t1, self.offset + self.counter)

