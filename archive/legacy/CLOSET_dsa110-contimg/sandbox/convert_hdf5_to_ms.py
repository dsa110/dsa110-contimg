import h5py
import numpy as np
from pyuvdata import UVData
import argparse
import os
from astropy.coordinates import EarthLocation
from astropy import units as u

def convert_hdf5_to_ms(hdf5_file, ms_file):
    """
    Converts a DSA-110 HDF5 visibility file to a CASA Measurement Set (MS).

    This function reads visibility data and metadata from an HDF5 file,
    formats it into a pyuvdata UVData object, and then writes it to a
    CASA Measurement Set (MS).

    Parameters
    ----------
    hdf5_file : str
        The path to the input HDF5 file.
    ms_file : str
        The path to the output MS file.

    Returns
    -------
    None
    """
    # Create a UVData object to store the data
    uvd = UVData()

    with h5py.File(hdf5_file, 'r') as hf:
        # Extract data and header information from the HDF5 file
        header = hf['Header']
        data = hf['Data']

        vis_data = data['visdata'][:]
        flags = data['flags'][:]
        nsamples = data['nsamples'][:]
        
        # Get dimensions from header
        uvd.Nants_data = int(header['Nants_data'][()])
        uvd.Nants_telescope = int(header['Nants_telescope'][()])
        uvd.Nbls = int(header['Nbls'][()])
        uvd.Nblts = int(header['Nblts'][()])
        uvd.Nfreqs = int(header['Nfreqs'][()])
        uvd.Npols = int(header['Npols'][()])
        uvd.Nspws = int(header['Nspws'][()])
        uvd.Ntimes = int(header['Ntimes'][()])

        # Antenna arrays
        uvd.ant_1_array = header['ant_1_array'][:]
        uvd.ant_2_array = header['ant_2_array'][:]
        uvd.antenna_diameters = header['antenna_diameters'][:]
        uvd.antenna_names = [name.decode('utf-8') for name in header['antenna_names'][:]]
        uvd.antenna_numbers = header['antenna_numbers'][:]
        uvd.antenna_positions = header['antenna_positions'][:]
        
        # Frequencies and polarizations
        uvd.channel_width = float(header['channel_width'][()])
        uvd.freq_array = header['freq_array'][:]
        uvd.polarization_array = header['polarization_array'][:]
        uvd.spw_array = header['spw_array'][:]
        
        # Time and UVW coordinates
        uvd.integration_time = header['integration_time'][:]
        uvd.time_array = header['time_array'][:]
        uvd.uvw_array = header['uvw_array'][:]
        
        # Telescope and object information
        uvd.instrument = header['instrument'][()].decode('utf-8')
        latitude_deg = float(header['latitude'][()])
        longitude_deg = float(header['longitude'][()])
        altitude_m = float(header['altitude'][()])
        # Set telescope location in ITRF (ECEF) meters
        loc = EarthLocation.from_geodetic(lon=longitude_deg * u.deg, lat=latitude_deg * u.deg, height=altitude_m * u.m)
        uvd.telescope_location = np.array([loc.x.to_value(u.m), loc.y.to_value(u.m), loc.z.to_value(u.m)])
        uvd.object_name = header['object_name'][()].decode('utf-8')
        uvd.telescope_name = header['telescope_name'][()].decode('utf-8')
        
        # Phase center information
        phase_type_value = header['phase_type'][()]
        uvd.phase_type = phase_type_value.decode('utf-8') if isinstance(phase_type_value, (bytes, bytearray)) else str(phase_type_value)

        # If the data are drift scan, do not set a fixed phase center RA/Dec.
        # If in the future the data are phased, prefer top-level keys first,
        # then fall back to extra_keywords, but only set them when truly phased.
        if uvd.phase_type.lower() == 'phased':
            ra_rad = None
            dec_rad = None
            # Try top-level datasets under Header
            if 'phase_center_ra' in header:
                ra_rad = float(header['phase_center_ra'][()])
            if 'phase_center_dec' in header:
                dec_rad = float(header['phase_center_dec'][()])
            # Fall back to extra_keywords if needed
            if (ra_rad is None or dec_rad is None) and 'extra_keywords' in header:
                extra_keywords = header['extra_keywords']
                if ra_rad is None and 'phase_center_ra' in extra_keywords:
                    ra_rad = float(extra_keywords['phase_center_ra'][()])
                # Some datasets store HA instead of RA; do not set RA from HA here without LST
                if ra_rad is None and 'ha_phase_center' in extra_keywords:
                    pass  # Insufficient info to convert HA->RA reliably here
                if dec_rad is None and 'phase_center_dec' in extra_keywords:
                    dec_rad = float(extra_keywords['phase_center_dec'][()])

            if ra_rad is not None and dec_rad is not None:
                uvd.phase_center_ra = ra_rad
                uvd.phase_center_dec = dec_rad


        # Reshape data arrays to match pyuvdata's expected format
        # (Nblts, Nspws, Nfreqs, Npols)
        vis_data = vis_data.reshape(uvd.Nblts, uvd.Nspws, uvd.Nfreqs, uvd.Npols)
        flags = flags.reshape(uvd.Nblts, uvd.Nspws, uvd.Nfreqs, uvd.Npols)
        nsamples = nsamples.reshape(uvd.Nblts, uvd.Nspws, uvd.Nfreqs, uvd.Npols)

        # Assign data to the UVData object
        uvd.data_array = vis_data
        uvd.flag_array = flags
        uvd.nsample_array = nsamples

        # Set history and other metadata
        uvd.history = 'Converted from DSA-110 HDF5 to MS using pyuvdata.'
        uvd.vis_units = 'Jy'  # Assuming the visibility units are Jy

    # Check the UVData object for correctness
    uvd.check()

    # Write the data to a Measurement Set
    # The write_ms method can handle the conversion.
    # It requires casacore to be installed, which is part of CASA.
    print(f"Writing data to {ms_file}")
    uvd.write_ms(ms_file, clobber=True)
    print("Conversion complete.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert DSA-110 HDF5 to CASA MS.')
    parser.add_argument('hdf5_file', type=str, help='Input HDF5 file.')
    parser.add_argument('ms_file', type=str, help='Output MS file.')
    args = parser.parse_args()

    # Ensure the output directory exists
    output_dir = os.path.dirname(args.ms_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    convert_hdf5_to_ms(args.hdf5_file, args.ms_file)
