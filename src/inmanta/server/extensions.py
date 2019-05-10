from typing import List

from inmanta.server.protocol import ServerSlice


class InvalidSliceNameException(Exception):

    pass


class ApplicationContext(object):
    def __init__(self) -> None:
        self._slices: List[ServerSlice] = []

    def register_slice(self, slice: ServerSlice) -> None:
        assert slice is not None
        self._slices.append(slice)

    def get_slices(self) -> List[ServerSlice]:
        return self._slices
