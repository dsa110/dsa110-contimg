"""aa_viewer: All-sky viewing utility for low-frequency compact radio interferometers."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

import healpy as hp
import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.visualization.wcsaxes.frame import EllipticalFrame
from astropy.wcs import WCS
from matplotlib import patheffects
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from ska_ost_low_uv.utils import import_optional_dependency

from ..aa_module import AaBaseModule
from ..coords.coord_utils import sky2hpix
from ..sky_model import generate_skycat, generate_skycat_solarsys

try:
    import_optional_dependency('sgp4', errors='warn')
    from ..coords.satellites import Satrec, compute_satellite_radec

    HAS_SGP4 = True
except ImportError:  # pragma: no cover
    HAS_SGP4 = False
    Satrec = None
    raise

# Making a colormap from SKAO color palette
skao_cmap = LinearSegmentedColormap.from_list('', ['#000000', '#070068', '#e70068', '#ffffff'])

###################
# ALL-SKY VIEWER
###################


class AllSkyViewer(AaBaseModule):
    """An all-sky imager based on matplotlib imshow with WCS support."""

    def __init__(
        self,
        observer: ApertureArray = None,
        skycat: dict = None,
        ts: Time = None,
        f_mhz: float = None,
        n_pix: int = 128,
    ):
        """Create a new AllSkyViewer.

        Args:
            observer (ApertureArray): Default ApertureArray object to use
            skycat (dict): A dictionary of SkyCoord / RadioSource objects.
                           These sources can be overlaid on images.
            ts (Time): Astropy Time of observation, used for coordinate calcs.
            f_mhz (float): Frequency in MHz of observation.
            n_pix (int): Number of pixels in image. Default 128. This should update
                         automatically if larger images are passed for viewing.
        """
        self.observer = observer
        self.skycat = skycat if skycat is not None else generate_skycat(observer)
        self.name = observer.name if hasattr(observer, 'name') else 'allsky'

        self.ts = ts
        self.f_mhz = f_mhz
        self.n_pix = n_pix
        self.name = 'All Sky Viewer'
        self._update_wcs()

    def _update_wcs(self):
        """Update World Coordinate System (WCS) information."""
        zen_sc = self.observer.coords.get_zenith()

        self.wcsd = {
            'SIMPLE': 'T',
            'NAXIS': 2,
            'NAXIS1': self.n_pix,
            'NAXIS2': self.n_pix,
            'CTYPE1': 'RA---SIN',
            'CTYPE2': 'DEC--SIN',
            'CRPIX1': self.n_pix // 2 + 1,
            'CRPIX2': self.n_pix // 2 + 1,
            'CRVAL1': zen_sc.icrs.ra.to('deg').value,
            'CRVAL2': zen_sc.icrs.dec.to('deg').value,
            'CDELT1': -360 / np.pi / self.n_pix,
            'CDELT2': 360 / np.pi / self.n_pix,
        }

        self.wcs = WCS(self.wcsd)

    def _update_skycat(self):
        """Update skycat with solar system objects."""
        # Update Sun/Moon position (if needed)
        sm = generate_skycat_solarsys(self.observer)
        for key in sm.keys():
            if key in self.skycat.keys():
                self.skycat[key] = sm[key]

    def update(self):
        """Update WCS information on timestamp or other change."""
        self._update_wcs()
        self._update_skycat()

    def get_pixel(self, src: SkyCoord) -> tuple[int]:
        """Return the pixel index for a given SkyCoord.

        Args:
            src (SkyCoord): sky coordinate of interest

        Returns:
            idx (tuple): pixel index corresponding to source location
        """
        self._update_wcs()

        # WAR: world_to_pixel doesn't seem to like the Sun's GCRS coords
        if src.frame.name == 'gcrs':
            src = SkyCoord(src.ra, src.dec)
        x, y = self.wcs.world_to_pixel(src)
        if ~np.isnan(x) and ~np.isnan(y):
            i, j = int(np.round(x)), int(np.round(y))
            return (j, i)  # flip so you can use as numpy index
        else:
            return (0, 0)

    def get_pixel_healpix(self, n_side: int, src: SkyCoord) -> int:
        """Return the healpix pixel index for a given SkyCoord.

        Args:
            src (SkyCoord): sky coordinate of interest
            n_side (int): Healpix NSIDE parameter

        Returns:
            idx (tuple): pixel index corresponding to source location
        """
        return sky2hpix(n_side, src)

    def load_labels(self, label_dict: dict):
        """Load a sky catalog.

        Args:
            label_dict (dict): Dictionary of RadioSources or SkyCoords
        """
        self.skycat = label_dict

    def new_fig(self, size: int = 6):
        """Create new matplotlib figure."""
        fig = plt.figure(self.name, figsize=(size, size), frameon=False)
        return fig

    def orthview(
        self,
        data: np.array = None,
        pol_idx: int = 0,
        sfunc: np.ufunc = None,
        overlay_srcs: bool = False,
        overlay_grid: bool = True,
        overlay_coords: str = 'icrs',
        return_data: bool = False,
        title: str = None,
        colorbar: bool = False,
        cmap: str = None,
        subplot_id: tuple = None,
        figsize: tuple = (4, 6),
        reuse_fig: bool = False,
        **kwargs,
    ):
        """Plot all-sky image.

        Args:
            data (np.array): Data to plot. Shape (N_pix, N_pix, N_pol). If not set, an image
                             will be generated from the ApertureArray object
            sfunc (np.unfunc): Scaling function to use, e.g. np.log, np.log10
            pol_idx (int): Polarization index to plot
            return_data (bool): If true, will return plot data as np array

        Plotting args:
            title (str): Title of plot. If not set, a title will be generated from LST and frequency.
            overlay_srcs (bool): Overlay sources in sky catalog (Default False)
            overlay_grid (bool): Overlay grid (Default true)
            overlay_coords (str): Coordinate system to use for overlay ('icrs', 'galactic', or 'altaz')
            colorbar (bool): Show colorbar (default False)
            cmap (str): Colormap to use, e.g. viridis, plasma. Also supports 'skao' custom colormap
            subplot_id (tuple): Subplot ID, e.g. (2,2,1). Use if making multi-panel figures
            reuse_fig (bool): Reuse figure if True, else create new figure.
            figsize (tuple): Figure size, e.g. (6, 4).
            **kwargs: These are passed on to imshow()

        """
        if data is None:
            data = self.observer.imaging.make_image(self.n_pix, update=True)

        if sfunc is None:
            sfunc = np.float32

        if data.shape[0] != self.n_pix:
            self.n_pix = data.shape[0]
            self.update()

        if cmap is not None:
            kwargs['cmap'] = cmap
            if cmap.lower() == 'skao':
                kwargs['cmap'] = skao_cmap

        # Update WCS and then create imshow
        self._update_wcs()
        if not reuse_fig:
            plt.figure(figsize=figsize)
        if subplot_id is not None:
            ax = plt.subplot(*subplot_id, projection=self.wcs, frame_on=False)
        else:
            ax = plt.subplot(projection=self.wcs, frame_class=EllipticalFrame)

        if data.ndim == 2:
            im = plt.imshow(sfunc(data), **kwargs)
        elif data.ndim == 3:
            im = plt.imshow(sfunc(data[..., pol_idx]), **kwargs)
        else:
            raise RuntimeError(f'Invalid image dimensions {data.shape}')

        # Create title
        if title is None:
            ts = self.observer._ws('t')
            f = self.observer._ws('f')
            lst_str = str(ts.sidereal_time('apparent'))
            title = f'{self.name}:  {ts.iso}  \n LST: {lst_str}  |  freq: {f.to("MHz").value:.2f} MHz'
        plt.title(title)

        # Overlay a grid onto the imshow
        path_effects = [patheffects.withStroke(linewidth=3, foreground='black')]
        if overlay_grid:
            if overlay_coords.lower() == 'icrs':
                ax.coords['ra'].set_ticklabel(color='white', path_effects=path_effects)
                ax.coords['dec'].set_ticklabel(color='white', path_effects=path_effects)
                ax.coords.grid(color='white', ls='dotted', alpha=0.8)
            elif overlay_coords.lower() == 'galactic':
                overlay = ax.get_coords_overlay('galactic')
                overlay[0].set_ticklabel(color='white', path_effects=path_effects)
                overlay[1].set_ticklabel(color='white', path_effects=path_effects)
            elif overlay_coords.lower() == 'altaz':
                t = self.observer.t[self.observer.idx['t']]
                overlay = ax.get_coords_overlay(AltAz(obstime=t, location=self.observer.earthloc))
                overlay.grid(color='white', ls='dotted', alpha=0.8)

                # Turn off RA/Dec ticks
                ax.coords['ra'].set_ticks_visible(False)
                ax.coords['ra'].set_ticklabel_visible(False)
                ax.coords['dec'].set_ticks_visible(False)
                ax.coords['dec'].set_ticklabel_visible(False)

                # Set Alt/Az ticks
                overlay[0].set_ticklabel(color='white', path_effects=path_effects)
                overlay[1].set_ticklabel(color='white', path_effects=path_effects)
                overlay[0].set_ticks_visible(False)
                overlay[1].set_ticks(
                    u.Quantity([0, 15, 30, 45, 60, 75, 80, 85], unit='deg'),
                    alpha=0,
                    color='white',
                )

            ax.coords.frame.set_color('white')

        # Overlay sources in skycat onto image
        if overlay_srcs:
            for src, src_sc in self.skycat.items():
                # Support satellites
                if HAS_SGP4:
                    if isinstance(src_sc, Satrec):
                        src_sc = compute_satellite_radec(self.observer, src_sc)
                x, y = self.wcs.world_to_pixel(src_sc)
                if not np.isnan(x) and not np.isnan(y):
                    plt.scatter(x, y, marker='x', color='red')
                    plt.text(x + 3, y + 3, src, color='#DDDDDD')

        # Turn on colorbar if requested
        if colorbar is True:
            plt.colorbar(im, orientation='horizontal')

        if return_data:
            return data

    def orthview_gsm(self, *args, **kwargs):
        """View diffuse sky model (Orthographic)."""
        return self.observer.simulation.orthview_gsm(*args, **kwargs)

    def mollview_gsm(self, *args, **kwargs):
        """View diffuse sky model (Mollweide)."""
        return self.observer.simulation.mollview_gsm(*args, **kwargs)

    def mollview(
        self,
        hmap: np.array = None,
        sfunc: np.ufunc = None,
        n_side: int = 64,
        fov: float = np.pi / 2,
        apply_mask: bool = True,
        pol_idx: int = 0,
        title: str = None,
        overlay_srcs: bool = False,
        overlay_grid: bool = True,
        colorbar: bool = False,
        cmap: str = None,
        **kwargs,
    ):
        """Plot a healpix map in mollweide projection (healpy.mollview).

        Args:
            hmap (np.array): Healpix to plot. Shape (N_hpx, N_pol). If not set, an healpix map
                             will be generated from the ApertureArray object
            sfunc (np.unfunc): Scaling function to use, e.g. np.log, np.log10
            pol_idx (int): Polarization index to plot
            n_side (int): Healpix NSIDE parameter. Only used if hmap is not supplied.
            fov (float): Field of view, in radians (distance from center pizel).
                         Defaults to pi/2 (90 degrees), which covers full sky.
                         Only used if hmap is not supplied.
            apply_mask (bool): Apply mask outside FoV. Default True.
                               Only used if hmap is not supplied.

        Plotting args:
            title (str): Title of plot. If not set, a title will be generated from LST and frequency.
            overlay_srcs (bool): Overlay sources in sky catalog (Default False)
            overlay_grid (bool): Overlay grid (Default true)
            colorbar (bool): Show colorbar (default False)
            cmap (str): Colormap to use, e.g. viridis, plasma. Also supports 'skao' custom colormap
            **kwargs: These are passed on to mollview()
        """
        if sfunc is None:
            sfunc = np.float32

        if hmap is None:
            hmap = self.observer.imaging.make_healpix(n_side=n_side, fov=fov, apply_mask=apply_mask)
        else:
            n_side = hp.npix2nside(hmap.shape[0])

        # Create title
        if title is None:
            ts = self.observer._ws('t')
            f = self.observer._ws('f')
            lst_str = str(ts.sidereal_time('apparent'))
            title = f'{self.name}:  {ts.iso} | LST: {lst_str}  |  freq: {f.to("MHz").value:.3f} MHz'

        if colorbar:
            kwargs['cbar'] = True

        if cmap is not None:
            kwargs['cmap'] = cmap
            if cmap.lower() == 'skao':
                kwargs['cmap'] = skao_cmap

        coord = kwargs.get('coord', 'G')

        if hmap.ndim == 1:
            hp.mollview(sfunc(hmap), coord=coord, title=title, **kwargs)
        else:
            hp.mollview(sfunc(hmap[..., pol_idx]), coord=coord, title=title, **kwargs)

        if overlay_grid:
            hp.graticule(color='white')

        if overlay_srcs:
            for src, src_sc in self.skycat.items():
                # Don't plot the source if it is outside FoV, or otherwise masked
                show_src = True

                # Support satellites
                if HAS_SGP4:
                    if isinstance(src_sc, Satrec):
                        src_sc = compute_satellite_radec(self.observer, src_sc)

                if isinstance(hmap, np.ma.core.MaskedArray):
                    if hmap.mask[sky2hpix(n_side, src_sc), pol_idx]:
                        show_src = False
                if hmap[sky2hpix(n_side, src_sc), pol_idx] == 0 or np.isinf(
                    hmap[sky2hpix(n_side, src_sc), pol_idx]
                ):
                    show_src = False

                if show_src:
                    hp.projscatter(
                        src_sc.galactic.l.deg,
                        src_sc.galactic.b.deg,
                        lonlat=True,
                        marker='x',
                        color='red',
                    )
                    hp.projtext(
                        src_sc.galactic.l.deg - 2,
                        src_sc.galactic.b.deg + 2,
                        s=src,
                        color='#DDDDDD',
                        lonlat=True,
                    )

    def write_fits(self, img_data: np.array, fn: str, pol_idx: int = 0):
        """Write image to FITS. Supports both healpix and regular images.

        Args:
            img_data (np.array): Image data to write
                                Note shape is (Npix, Npix, Npol)
            fn (str): Image filename
            pol_idx (int): Polarization
        """
        if img_data.ndim == 2:
            hp.fitsfunc.write_map(fn, img_data[..., pol_idx])
        else:
            self.n_pix = img_data.shape[0]
            self.update()
            h = self.wcs.to_header()
            h.add_comment(f'TELESCOPE: {self.observer.name}')
            h.add_comment(f'OBSDATA: {self.observer._ws("t").isot}')
            h.add_comment(f'OBSFREQ: {self.observer._ws("f").to("MHz")}')
            h.add_comment(f'POL_PROD: {self.observer._ws("p")}')

            d = np.nan_to_num(img_data[..., pol_idx])

            hdu = fits.PrimaryHDU(header=h, data=d)
            hdu.writeto(fn)
