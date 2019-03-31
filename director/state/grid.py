from band import logger
from band import logger
from ..helpers import nn, merge_dicts
from ..constants import (
    DEFAULT_COL, DEFAULT_ROW)
from ..structs import ServicePostion

def is_valid_pos(pos):
    if pos:
        if isinstance(pos, ServicePostion):
            return True
        elif isinstance(pos, dict):
            if pos.get('col') is not None and pos.get('row') is not None:
                return True


class ServicesGrid:

    """
    Dashboard tile
    """
    def __init__(self, manager):
        self.manager = manager
        self.cols = 6
        self.rows = 6

    @property
    def default_pos(self):
        return dict(col=DEFAULT_COL, row=DEFAULT_ROW)

    def _occupied(self, exclude=None):
        """
        Building list of occupied positions
        """
        occupied = []
        for srv in self.manager.values():
            if srv.name != exclude and nn(srv.pos.col) and nn(srv.pos.row):
                occupied.append(srv.pos.to_s())
        return occupied


    def allocate(self, name, col, row):
        """
        Allocating dashboard position for container close to wanted
        """
        occupied = self._occupied(exclude=name)
        for icol, irow in self._space_walk(int(col), int(row)):
            key = f"{icol}x{irow}"
            if key not in occupied:
                logger.debug(f'Allocatted position', name=name, pos=f"{col}x{row}", occupied=occupied, allocated=f"{icol}x{irow}")
                return dict(col=icol, row=irow)


    def _space_walk(self, scol=0, srow=0):
        """
        Generator over all pissible postions starting from specified location
        """
        srow = int(srow)
        scol = int(scol)
        # first part
        for rowi in range(srow, self.rows):
            for coli in range(scol, self.cols):
                yield coli, rowi
        # back side
        for rowi in range(0, srow):
            for coli in range(0, scol):
                yield coli, rowi
