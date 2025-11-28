"""
Visualization tools for fast transient imaging.

Based on VAST fast transient pipeline (vast-fastdetection) plotting tools,
adapted for DSA-110 and removed aplpy dependency.
"""

import glob
import logging
import os

import matplotlib.animation as animation
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.time import Time
from astropy.visualization import ImageNormalize, ZScaleInterval
from astropy.wcs import WCS

# Configure logging
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


def get_image_list(base_name: str) -> list:
    """Get list of fast images for a given base MS name."""
    # Match pattern: basename.fast-t*-image.fits
    pattern = f"{base_name}.fast-t*-image.fits"
    images = sorted(glob.glob(pattern))
    if not images:
        # Try assuming base_name is the prefix without .ms
        pattern = f"{base_name}*.fast-t*-image.fits"
        images = sorted(glob.glob(pattern))
    return images


def extract_lightcurve(image_list: list, ra_deg: float, dec_deg: float, radius_pix: int = 2):
    """Extract lightcurve for a specific position."""
    times = []
    fluxes = []
    rmses = []

    coord = SkyCoord(ra_deg, dec_deg, unit=u.deg)

    for img_file in image_list:
        with fits.open(img_file) as hdul:
            header = hdul[0].header
            data = hdul[0].data.squeeze()
            wcs = WCS(header).celestial

            # Get timestamp
            if "DATE-OBS" in header:
                times.append(Time(header["DATE-OBS"]))
            else:
                # Fallback or handle error
                times.append(Time.now())  # Placeholder

            # Convert sky to pixel
            x, y = wcs.world_to_pixel(coord)
            x, y = int(np.round(x)), int(np.round(y))

            # Check bounds
            if 0 <= x < data.shape[1] and 0 <= y < data.shape[0]:
                val = data[y, x]
                fluxes.append(val)

                # Simple local RMS
                y_min = max(0, y - 10)
                y_max = min(data.shape[0], y + 10)
                x_min = max(0, x - 10)
                x_max = min(data.shape[1], x + 10)
                local_region = data[y_min:y_max, x_min:x_max]
                rmses.append(np.std(local_region))
            else:
                fluxes.append(np.nan)
                rmses.append(np.nan)

    return times, np.array(fluxes), np.array(rmses)


def plot_lightcurve(
    times: list,
    fluxes: np.ndarray,
    rmses: np.ndarray,
    output_file: str,
    title: str = "Transient Lightcurve",
):
    """Plot and save lightcurve."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Convert to mJy
    fluxes_mjy = fluxes * 1000
    rmses_mjy = rmses * 1000

    # Convert times to plot dates
    plot_dates = [t.datetime for t in times]

    ax.errorbar(plot_dates, fluxes_mjy, yerr=rmses_mjy, fmt="o-", capsize=3)

    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Flux Density (mJy/beam)")
    ax.set_title(title)

    # Format x-axis
    date_format = mdates.DateFormatter("%H:%M:%S")
    ax.xaxis.set_major_formatter(date_format)
    fig.autofmt_xdate()

    ax.grid(True, linestyle="--", alpha=0.5)

    plt.savefig(output_file, dpi=150)
    plt.close(fig)
    LOG.info(f"Saved lightcurve to {output_file}")


def make_cutout_movie(
    image_list: list, ra_deg: float, dec_deg: float, output_file: str, fov_arcmin: float = 5.0
):
    """Generate an animated GIF of the source."""
    fig = plt.figure(figsize=(6, 6))
    ims = []

    coord = SkyCoord(ra_deg, dec_deg, unit=u.deg)

    # Determine normalization from first few images
    all_vals = []
    for img in image_list[:5]:
        with fits.open(img) as hdul:
            all_vals.append(hdul[0].data.flatten())
    all_vals = np.concatenate(all_vals)
    vmin, vmax = np.percentile(all_vals, [1, 99])

    for i, img_file in enumerate(image_list):
        with fits.open(img_file) as hdul:
            data = hdul[0].data.squeeze()

            # Skip empty frames (all zeros)
            if np.nanmax(data) == 0 and np.nanmin(data) == 0:
                continue

            header = hdul[0].header
            wcs = WCS(header).celestial

            # Create cutout
            try:
                cutout = Cutout2D(data, coord, (fov_arcmin * u.arcmin), wcs=wcs)

                if i == 0:
                    ax = fig.add_subplot(111, projection=cutout.wcs)
                    ax.set_xlabel("RA")
                    ax.set_ylabel("Dec")

                # Plot
                im = ax.imshow(
                    cutout.data * 1000,  # mJy
                    origin="lower",
                    cmap="inferno",
                    vmin=vmin * 1000,
                    vmax=vmax * 1000,
                    animated=True,
                )

                # Label
                time_str = header.get("DATE-OBS", f"Frame {i}")
                # If it's a full ISO string, truncate it
                if "T" in time_str:
                    time_str = time_str.split("T")[1]

                label = ax.text(
                    0.05, 0.95, time_str, transform=ax.transAxes, color="white", fontweight="bold"
                )

                ims.append([im, label])

            except Exception as e:
                LOG.warning(f"Failed to cutout frame {i}: {e}")
                continue

    if ims:
        ani = animation.ArtistAnimation(fig, ims, interval=200, blit=True, repeat_delay=1000)
        ani.save(output_file, writer="imagemagick", dpi=100)
        LOG.info(f"Saved movie to {output_file}")
    else:
        LOG.error("No frames generated for movie")
    plt.close(fig)


def make_stamp_grid(
    image_list: list,
    ra_deg: float,
    dec_deg: float,
    output_file: str,
    fov_arcmin: float = 5.0,
    max_frames: int = 25,
):
    """Create a static grid of cutouts."""
    n_images = min(len(image_list), max_frames)
    n_cols = 5
    n_rows = int(np.ceil(n_images / n_cols))

    fig = plt.figure(figsize=(15, 3 * n_rows))

    coord = SkyCoord(ra_deg, dec_deg, unit=u.deg)

    # Get global scaling
    with fits.open(image_list[0]) as hdul:
        data = hdul[0].data.squeeze()
        vmin, vmax = np.percentile(data, [1, 99])

    for i in range(n_images):
        img_file = image_list[i]
        with fits.open(img_file) as hdul:
            data = hdul[0].data.squeeze()
            header = hdul[0].header
            wcs = WCS(header).celestial

            try:
                cutout = Cutout2D(data, coord, (fov_arcmin * u.arcmin), wcs=wcs)

                ax = fig.add_subplot(n_rows, n_cols, i + 1, projection=cutout.wcs)

                im = ax.imshow(
                    cutout.data * 1000,
                    origin="lower",
                    cmap="inferno",
                    vmin=vmin * 1000,
                    vmax=vmax * 1000,
                )

                # Simple labeling
                ax.set_xlabel("")
                ax.set_ylabel("")
                ax.coords[0].set_ticklabel_visible(False)
                ax.coords[1].set_ticklabel_visible(False)

                time_str = header.get("DATE-OBS", "").split("T")[-1]
                ax.set_title(time_str, fontsize=8)

            except Exception as e:
                continue

    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close(fig)
    LOG.info(f"Saved stamp grid to {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visualize fast transient images")
    parser.add_argument("basename", help="Base name of the fast images (e.g., path/to/obs.ms)")
    parser.add_argument("--ra", type=float, required=True, help="RA in degrees")
    parser.add_argument("--dec", type=float, required=True, help="Dec in degrees")
    parser.add_argument("--out", default=".", help="Output directory")

    args = parser.parse_args()

    images = get_image_list(args.basename)
    if not images:
        print(f"No images found for {args.basename}")
        exit(1)

    print(f"Found {len(images)} images")

    if not os.path.exists(args.out):
        os.makedirs(args.out)

    base_out = os.path.join(args.out, f"transient_{args.ra}_{args.dec}")

    # 1. Lightcurve
    times, fluxes, rmses = extract_lightcurve(images, args.ra, args.dec)
    plot_lightcurve(times, fluxes, rmses, f"{base_out}_lightcurve.png")

    # 2. Movie
    make_cutout_movie(images, args.ra, args.dec, f"{base_out}_movie.gif")

    # 3. Grid
    make_stamp_grid(images, args.ra, args.dec, f"{base_out}_grid.png")
