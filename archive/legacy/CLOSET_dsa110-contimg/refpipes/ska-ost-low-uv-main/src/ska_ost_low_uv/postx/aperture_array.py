"""aperture_array: Basic antenna array geometry class."""

import numpy as np
from astropy.time import Time
from astropy.units import Quantity
from loguru import logger
from pygdsm import init_observer

from ska_ost_low_uv.datamodel import UVX, UVXAntennaCal
from ska_ost_low_uv.datamodel.uvx import create_empty_uvx
from ska_ost_low_uv.io import read_cal
from ska_ost_low_uv.vis_utils import vis_arr_to_matrix_4pol

from .aa_module import AaBaseModule
from .aa_plotting import AaPlotter
from .calibration.aa_calibration import AaCalibrator
from .coords.aa_coords import AaCoords
from .imaging.aa_imaging import AaImager
from .simulation.aa_simulation import AaSimulator
from .viewer.aa_viewer import AllSkyViewer


class ApertureArray(AaBaseModule):
    """RadioArray class, designed for post-correlation beamforming and all-sky imaging."""

    def __init__(
        self,
        uvx: UVX = None,
        verbose: bool = False,
        gsm: str = 'gsm08',
        station_id: str = None,
        sim_f: Quantity = None,
        sim_t: Time = None,
    ):
        """Initialize RadioArray class (based on astropy EarthLocation).

        Args:
            uvx (UVX):               datamodel visibility dataclass, UVX. Needed unless station_id is set.
            verbose (bool):          Print extra details to screen
            gsm (str):               Name of global sky model (gsm08, gsm16, lfsm, haslam)
            station_id (str):        Optional station ID to use to load basic config, instead of UVX
            sim_f (Quantity):        Frequency array to use for simulation. Only use if not loading UVX.
            sim_t (Time):            Time array to use for simulation. Only use if not loading UVX.
        """
        # fmt: off
        self.verbose        = verbose

        if uvx is None:
            uvx = create_empty_uvx(station_id, f=sim_f, t=sim_t)

        self.uvx            = uvx
        self.name           = uvx.name
        self.earthloc       = uvx.origin

        xyz0 = uvx.antennas.attrs['array_origin_geocentric'].data
        self.xyz_enu   = uvx.antennas.enu.data
        self.xyz_ecef  = uvx.antennas.ecef.data + xyz0

        self.n_ant     = len(self.xyz_enu)
        self.ant_names = uvx.antennas.identifier

        # Setup frequency, time, and phase centre
        self.f = Quantity(uvx.data.coords['frequency'].data, 'Hz')
        self.t = uvx.timestamps
        self.p = uvx.data.polarization.values

        # Phase center
        self.phase_center = uvx.phase_center

        # Setup current index dict and workspace
        self.idx = {'t': 0, 'f': 0, 'p': 0}
        self.workspace = {}

        self.bl_matrix = self._generate_bl_matrix()

        # Healpix workspace
        self._to_workspace('hpx', {})

        # Add-on modules
        self.coords      = AaCoords(self)
        self.plotting    = AaPlotter(self)
        self.viewer      = AllSkyViewer(self)
        self.simulation  = AaSimulator(self)
        self.calibration = AaCalibrator(self)
        self.imaging     = AaImager(self)

        # Setup Global Sky Model
        self.set_gsm(gsm)
        # fmt: off

    def __repr__(self):
        """Display representation of ApertureArray object."""
        eloc = self.earthloc.to_geodetic()
        s = f'<ApertureArray: {self.name} (lat {eloc.lat.value:.2f}, lon {eloc.lon.value:.2f})>'
        return s

    def set_gsm(self, gsm_str: str = 'gsm08'):
        """Set the Global Sky Model to use."""
        self.simulation.model.gsm = init_observer(gsm_str)
        self.simulation.model.gsm.lat = self.uvx.origin.lat.to('rad').value
        self.simulation.model.gsm.lon = self.uvx.origin.lon.to('rad').value
        self.simulation.model.gsm.elev = self.uvx.origin.height.to('m').value
        self.simulation.model.gsm.date = self.t[0].datetime
        self.gsm = self.simulation.model.gsm

    def set_idx(self, f: int = None, t: int = None, p: int = None):
        """Set index of UVX data array.

        Args:
            f (int): Frequency index
            t (int): Time index
            p (int): Polarization index

        Notes:
            Updates the self.idx dictionary (keys are f,t,p).
            This controls which data are selected by generate_vis_matrix()
        """
        if f is not None:
            self.idx['f'] = f
        if t is not None:
            self.idx['t'] = t
        if p is not None:
            self.idx['p'] = p

    def _ws(self, key: str):
        """Return value of current index for freq / pol / time or workspace entry.

        Helper function to act as 'workspace'.
        Uses self.idx dictionary which stores selected index

        Args:
            key (str): One of f (freq), p (pol) or t (time)

        Returns:
            Value of f/p/t array at current index in workspace

        """
        if key in ('f', 'p', 't'):
            return self.__getattribute__(key)[self.idx[key]]
        else:
            return self.workspace[key]

    def _in_workspace(self, key: str) -> bool:
        # Check if key is in workspace
        return key in self.workspace

    def _to_workspace(self, key: str, val):
        self.workspace[key] = val

    def _generate_bl_matrix(self):
        """Compute a matrix of baseline lengths."""

        # Helper fn to compute length for one row
        def bl_len(xyz, idx):
            return np.sqrt(np.sum((xyz - xyz[idx]) ** 2, axis=-1))

        bls = np.zeros((self.n_ant, self.n_ant), dtype='float32')
        # Loop over rows
        for ii in range(256):
            bls[ii] = bl_len(self.xyz_enu, ii)
        return bls

    def set_cal(self, cal: UVXAntennaCal):
        """Set gaincal solution (used when generating vis matrix).

        Args:
            cal (UVXAntennaCal): Calibration to apply
        """
        if cal is not None:
            f_cal = Quantity(cal.gains.frequency, cal.gains.frequency.attrs['units'])
            f_match = np.allclose(self.f, f_cal)
            a_match = len(self.ant_names.values) == len(cal.gains.antenna.values)
            n_match = self.name == cal.telescope

            if not f_match:
                e = 'Calibration frequencies do not match!'
                logger.error(e)
                raise RuntimeError(e)
            if not a_match:
                e = 'Antenna IDs in cal file do not match!'
                logger.error(e)
                raise RuntimeError(e)
            if not n_match:
                logger.warning(f'Calibration is from {cal.telescope}, array name is {self.name}')

        # Cal can be set to None by the user
        self.workspace['cal'] = cal

    def load_cal(self, cal_filename: str) -> UVXAntennaCal:
        """Load a UVXAntennaCal from a file and set it to be used.

        Args:
            cal_filename (str): Path to uvx antenna cal file

        Returns:
            cal (UVXAntennaCal): Antenna calibration and flags
        """
        cal = read_cal(cal_filename)
        self.set_cal(cal)
        return cal

    def generate_vis_matrix(
        self, vis: str = 'data', t_idx=None, f_idx=None, include_autos: bool = True
    ) -> np.array:
        """Generate visibility matrix from underlying array data.

        Underlying UVX data has axes (time, frequency, baseline, polarization)
        Model data should have axes (time, frequency, antenna1, antenna2) and be an xr.DataArray

        Args:
            vis (str): Select visibilities to be either raw 'data', calibrated 'corrected', or 'model'
            t_idx (int): Time index for data
            f_idx (int): Frequency index for data
            include_autos (bool): If False, autocorrelation products will be set to zero.

        Returns:
            vis_mat (np.array): Visibility data
        """
        t_idx = self.idx['t'] if t_idx is None else t_idx
        f_idx = self.idx['f'] if f_idx is None else f_idx
        match vis:
            case 'corrected':
                vis_mat = self.workspace['vis']['corrected']
            case 'data':
                vis_sel = self.uvx.data[t_idx, f_idx].values
                vis_mat = vis_arr_to_matrix_4pol(vis_sel, self.n_ant)
            case 'cal':
                vis_sel = self.uvx.data[t_idx, f_idx].values
                vis_mat = vis_arr_to_matrix_4pol(vis_sel, self.n_ant)
                if 'cal' in self.workspace.keys():
                    vis_mat *= self.workspace['cal'].to_matrix()
                else:
                    logger.warning('Calibration not set, returning raw visibilities.')
            case 'model':
                vis_mat = self.simulation.model.visibilities[t_idx, f_idx]

        # Blank out autocorrelations if include_autos=False
        if not include_autos:
            diags = np.diag_indices(vis_mat.shape[0])
            vis_mat[diags] = 0

        return vis_mat
