from dsa110_contimg.utils.constants import OVRO_LOCATION
from dsa110_contimg.utils.antpos_local import get_itrf
from pyuvdata import UVData

class BaseWriter:
    def __init__(self, uvdata: UVData, output_path: str, **kwargs):
        self.uvdata = uvdata
        self.output_path = output_path
        self.writer_kwargs = kwargs

    def write(self):
        raise NotImplementedError("Subclasses should implement this method.")


class ParallelSubbandWriter(BaseWriter):
    def write(self):
        # Implement parallel writing logic for subband data
        pass


class PyuvdataWriter(BaseWriter):
    def write(self):
        # Implement writing logic using pyuvdata
        pass


def get_writer(writer_type: str):
    if writer_type == 'parallel-subband':
        return ParallelSubbandWriter
    elif writer_type == 'pyuvdata':
        return PyuvdataWriter
    else:
        raise ValueError(f"Unknown writer type: {writer_type}")