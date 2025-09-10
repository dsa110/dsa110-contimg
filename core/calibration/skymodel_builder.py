import os
from typing import List

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from pyradiosky import SkyModel


class SkyModelBuilder:
    def __init__(self, output_dir: str = 'data/sky_models') -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def build_point_sources(self,
                            names: List[str],
                            ras_deg: List[float],
                            decs_deg: List[float],
                            fluxes_jy: List[float],
                            ref_freq_hz: float) -> SkyModel:
        coords = SkyCoord(ra=ras_deg * u.deg, dec=decs_deg * u.deg, frame='icrs')
        stokes = [[f, 0.0, 0.0, 0.0] for f in fluxes_jy]
        sm = SkyModel(
            name=names,
            skycoord=coords,
            stokes=(u.Quantity(stokes, unit=u.Jy).T),
            spectral_type='flat',
        )
        # Attach a reference frequency array of length Ncomponents
        sm.reference_frequency = (np.ones(len(names)) * ref_freq_hz) * u.Hz
        return sm

    def write_casa_component_list(self, sm: SkyModel, out_name: str) -> str:
        out_path = os.path.join(self.output_dir, f"{out_name}.cl")
        # Remove pre-existing artifact if present
        if os.path.exists(out_path):
            try:
                # component lists are CASA tables (directories)
                import shutil
                shutil.rmtree(out_path)
            except Exception:
                os.remove(out_path)
        from casatools import componentlist
        cl = componentlist()
        # Build in-memory list, then rename to out_path
        lon, lat = sm.get_lon_lat()
        flux_I = sm.stokes[0, 0, :].to_value(u.Jy)
        for i in range(sm.Ncomponents):
            ra_str = lon[i].to_string(unit=u.hour, sep='hms', precision=4)
            dec_str = lat[i].to_string(unit=u.deg, sep='dms', precision=3, alwayssign=True)
            cl.addcomponent(
                flux=float(flux_I[i]),
                fluxunit='Jy',
                dir=f"J2000 {ra_str} {dec_str}",
                shape='point',
                spectrumtype='constant'
            )
        # Write to disk
        cl.rename(out_path)
        cl.close()
        cl.done()
        return out_path
