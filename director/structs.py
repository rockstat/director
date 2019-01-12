from collections import namedtuple
from prodict import Prodict
from typing import List, NamedTuple

IMAGE_CATEGORIES = Prodict(user='user', collection='collection', base='base')

ImageObj = namedtuple('ImageObj', 'name category path')


class LogRecord(NamedTuple):
    id: int
    ts: int
    cid: str
    name: str
    source: str
    size: int
    message: str

class ServicePostion(namedtuple('ServicePostion', 'col row')):
    __slots__ = ()
    def __str__(self):
        return f"{self.col}x{self.row}"
    
    def get(self, key):
        return getattr(self, key)
    
    @classmethod
    def from_string(cls, pos_string):
        if pos_string:
            col, row = pos_string.split('x')
            if col != None and row != None:
                return cls(col, row)
        

class BuildOptions(Prodict):
    nocache: bool
    auto_remove: bool


class RunParams(Prodict):
    pos: ServicePostion
    build_options: BuildOptions

