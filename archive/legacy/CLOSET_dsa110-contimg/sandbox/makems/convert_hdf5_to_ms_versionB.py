import h5py
import numpy as np
from pyuvdata import UVData
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation

def hdf5_to_ms(hdf5_file, output_ms):
    """
    Convert DSA-110 HDF5 visibility file to CASA Measurement Set
    """
    
    # Initialize UVData object
    uv = UVData()
    
    # Read HDF5 file
    with h5py.File(hdf5_file, 'r') as f:
        # Read data
        visdata = f['Data/visdata'][:]  # Shape: (Nblts, Nspws, Nfreqs, Npols)
        flags = f['Data/flags'][:]
        nsamples = f['Data/nsamples'][:]
        
        # Read header metadata
        freq_array = f['Header/freq_array'][:]  # Shape: (Nspws, Nfreqs)
        time_array = f['Header/time_array'][:]  # Julian dates
        ant_1_array = f['Header/ant_1_array'][:]
        ant_2_array = f['Header/ant_2_array'][:]
        uvw_array = f['Header/uvw_array'][:]
        integration_time = f['Header/integration_time'][:]
        polarization_array = f['Header/polarization_array'][:]
        
        # Telescope metadata
        antenna_positions = f['Header/antenna_positions'][:]
        antenna_numbers = f['Header/antenna_numbers'][:]
        antenna_names = f['Header/antenna_names'][:]
        antenna_diameters = f['Header/antenna_diameters'][:]
        
        latitude = f['Header/latitude'][()]
        longitude = f['Header/longitude'][()]
        altitude = f['Header/altitude'][()]
        
        Nants_telescope = f['Header/Nants_telescope'][()]
        Nants_data = f['Header/Nants_data'][()]
        Nbls = f['Header/Nbls'][()]
        Nblts = f['Header/Nblts'][()]
        Nfreqs = f['Header/Nfreqs'][()]
        Npols = f['Header/Npols'][()]
        Nspws = f['Header/Nspws'][()]
        Ntimes = f['Header/Ntimes'][()]
        channel_width = f['Header/channel_width'][()]
    
    # Set telescope location
    telescope_location = EarthLocation.from_geodetic(
        lon=longitude*u.deg, 
        lat=latitude*u.deg, 
        height=altitude*u.m
    )
    
    # Populate UVData object
    uv.Nants_telescope = int(Nants_telescope)
    uv.Nants_data = int(Nants_data)
    uv.Nbls = int(Nbls)
    uv.Nblts = int(Nblts)
    uv.Nfreqs = int(Nfreqs)
    uv.Npols = int(Npols)
    uv.Nspws = int(Nspws)
    uv.Ntimes = int(Ntimes)
    
    # Time parameters
    uv.time_array = time_array
    uv.integration_time = integration_time
    uv.lst_array = np.zeros(Nblts)  # Calculate LST if needed
    
    # Baseline parameters
    uv.baseline_array = uv.antnums_to_baseline(ant_1_array, ant_2_array)
    uv.ant_1_array = ant_1_array.astype(int)
    uv.ant_2_array = ant_2_array.astype(int)
    uv.uvw_array = uvw_array.astype(float)
    
    # Frequency parameters
    uv.freq_array = freq_array.astype(float)  # Hz
    uv.channel_width = channel_width  # Hz
    uv.spw_array = np.array([0])  # Single spectral window for this subband
    
    # Polarization
    uv.polarization_array = polarization_array.astype(int)
    
    # Antenna parameters
    uv.antenna_numbers = antenna_numbers.astype(int)
    uv.antenna_names = [name.decode() if isinstance(name, bytes) else str(name) 
                        for name in antenna_names]
    uv.antenna_positions = antenna_positions.astype(float)
    uv.antenna_diameters = antenna_diameters.astype(float)
    
    # Telescope location (need to convert to ITRF XYZ)
    uv.telescope_location = np.array([
        telescope_location.x.to(u.m).value,
        telescope_location.y.to(u.m).value,
        telescope_location.z.to(u.m).value
    ])
    uv.telescope_location_lat_lon_alt = np.array([latitude, longitude, altitude])
    uv.telescope_location_lat_lon_alt_degrees = np.array([latitude, longitude, altitude])
    
    uv.telescope_name = 'OVRO_MMA'  # From your header
    uv.instrument = 'DSA'
    
    # Data arrays - reshape to (Nblts, Nspws, Nfreqs, Npols)
    uv.data_array = visdata
    uv.flag_array = flags
    uv.nsample_array = nsamples.astype(float)
    
    # Set other required metadata
    uv.vis_units = 'uncalib'  # or 'Jy' if calibrated
    uv.phase_type = 'drift'  # From your header
    uv.object_name = 'search'
    uv.history = f'Converted from {hdf5_file}'
    
    # Set phase center (zenith/drift mode)
    # You may need to adjust this based on your observation
    uv.phase_center_ra = None
    uv.phase_center_dec = None
    uv.phase_center_epoch = None
    
    # Run checks
    uv.check()
    
    # Write to Measurement Set
    print(f"Writing Measurement Set: {output_ms}")
    uv.write_ms(output_ms, force_phase='drift', flip_conj=False)
    
    print(f"Successfully converted {hdf5_file} to {output_ms}")
    
    return uv

# Example usage
if __name__ == '__main__':
    hdf5_file = '2025-09-05T03:23:14_sb00.hdf5'
    output_ms = '2025-09-05T03:23:14_sb00.ms'
    
    uv = hdf5_to_ms(hdf5_file, output_ms)