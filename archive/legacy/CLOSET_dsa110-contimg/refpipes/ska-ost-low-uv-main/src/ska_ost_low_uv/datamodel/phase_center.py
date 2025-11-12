"""phase_center.py -- Class for phase centers, based on SkyCoord."""

from astropy.coordinates import SkyCoord


class PhaseCenter(SkyCoord):
    """Define PhaseCenter object.

    Creates a superclass of SkyCoord with added 'phase_type' and 'name' attributes.
    """

    def __init__(self, *args, phase_type: str = 'drift', name: str = 'Zenith', **kwargs):
        """Initialize PhaseCenter.

        Args:
            phase_type (str): Type of phasing. Either 'drift' or 'track'.
            name (str): Name of phase center. Defaults to Zenith
            args: Arguments to pass to SkyCoord
            kwargs: Keyword arguments to pass to SkyCoord
        """
        self.name = name
        self.phase_type = phase_type
        super().__init__(*args, **kwargs)
