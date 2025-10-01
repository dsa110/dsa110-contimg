#!/usr/bin/env python3
"""
Test Data Generator for DSA-110 Pipeline

This module generates synthetic test data for comprehensive
testing of the DSA-110 continuum imaging pipeline.
"""

import os
import numpy as np
import h5py
import astropy.io.fits as fits
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.wcs import WCS
from astropy.table import Table
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from dsa110.utils.logging import get_logger

logger = get_logger(__name__)


class TestDataGenerator:
    """
    Generator for synthetic test data for DSA-110 pipeline testing.
    
    Creates realistic HDF5 files, FITS images, and other data products
    for comprehensive pipeline testing.
    """
    
    def __init__(self, output_dir: str = "/tmp/dsa110_test_data"):
        """
        Initialize the test data generator.
        
        Args:
            output_dir: Directory to save generated test data
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # DSA-110 specifications
        self.frequency_range = (1.0e9, 2.0e9)  # 1-2 GHz
        self.bandwidth = 100e6  # 100 MHz
        self.n_channels = 64
        self.n_antennas = 110
        self.observation_duration = 3600  # 1 hour in seconds
        
        # Generate antenna positions
        self.antenna_positions = self._generate_antenna_positions()
        
        # Generate source catalog
        self.source_catalog = self._generate_source_catalog()
    
    def _generate_antenna_positions(self) -> np.ndarray:
        """Generate DSA-110 antenna positions."""
        # Simplified antenna array layout
        # In practice, this would use the actual DSA-110 layout
        positions = []
        
        # Core array (compact)
        for i in range(50):
            angle = 2 * np.pi * i / 50
            radius = 50 + np.random.normal(0, 10)  # meters
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = np.random.normal(0, 5)  # meters
            positions.append([x, y, z])
        
        # Outer array (extended)
        for i in range(60):
            angle = 2 * np.pi * i / 60
            radius = 200 + np.random.normal(0, 20)  # meters
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = np.random.normal(0, 10)  # meters
            positions.append([x, y, z])
        
        return np.array(positions)
    
    def _generate_source_catalog(self) -> Table:
        """Generate a realistic source catalog."""
        sources = []
        
        # Bright sources
        bright_sources = [
            {'ra': 180.0, 'dec': 37.0, 'flux': 1.0, 'name': 'CygA'},
            {'ra': 180.1, 'dec': 37.1, 'flux': 0.5, 'name': 'CygB'},
            {'ra': 179.9, 'dec': 36.9, 'flux': 0.3, 'name': 'CygC'},
        ]
        
        # Faint sources
        for i in range(20):
            ra = 180.0 + np.random.normal(0, 0.1)
            dec = 37.0 + np.random.normal(0, 0.1)
            flux = np.random.exponential(0.01)
            name = f"Source_{i:03d}"
            
            sources.append({
                'ra': ra,
                'dec': dec,
                'flux': flux,
                'name': name
            })
        
        # Combine all sources
        all_sources = bright_sources + sources
        
        # Create astropy table
        table = Table()
        table['ra'] = [s['ra'] for s in all_sources]
        table['dec'] = [s['dec'] for s in all_sources]
        table['flux'] = [s['flux'] for s in all_sources]
        table['name'] = [s['name'] for s in all_sources]
        
        return table
    
    def generate_hdf5_files(self, n_files: int = 5, time_interval: float = 300.0) -> List[str]:
        """
        Generate synthetic HDF5 files for testing.
        
        Args:
            n_files: Number of HDF5 files to generate
            time_interval: Time interval between files in seconds
            
        Returns:
            List of generated HDF5 file paths
        """
        logger.info(f"Generating {n_files} HDF5 files")
        
        hdf5_files = []
        start_time = Time.now()
        
        for i in range(n_files):
            # Calculate timestamp
            timestamp = start_time + i * time_interval * u.second
            
            # Generate filename
            filename = f"dsa110_{timestamp.isot.replace(':', '').replace('-', '')}.h5"
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate HDF5 file
            self._create_hdf5_file(filepath, timestamp, i)
            hdf5_files.append(filepath)
            
            logger.info(f"Generated HDF5 file: {filename}")
        
        return hdf5_files
    
    def _create_hdf5_file(self, filepath: str, timestamp: Time, file_index: int):
        """Create a single HDF5 file with realistic data."""
        with h5py.File(filepath, 'w') as f:
            # Create main data group
            data_group = f.create_group('data')
            
            # Generate frequency channels
            frequencies = np.linspace(
                self.frequency_range[0],
                self.frequency_range[1],
                self.n_channels
            )
            
            # Generate time samples
            n_time_samples = 100
            time_samples = np.linspace(0, self.observation_duration, n_time_samples)
            
            # Generate visibility data
            vis_data = self._generate_visibility_data(
                frequencies, time_samples, file_index
            )
            
            # Store visibility data
            data_group.create_dataset('visibilities', data=vis_data)
            data_group.create_dataset('frequencies', data=frequencies)
            data_group.create_dataset('times', data=time_samples)
            
            # Store antenna positions
            data_group.create_dataset('antenna_positions', data=self.antenna_positions)
            
            # Store metadata
            f.attrs['timestamp'] = timestamp.isot
            f.attrs['frequency_range'] = self.frequency_range
            f.attrs['bandwidth'] = self.bandwidth
            f.attrs['n_channels'] = self.n_channels
            f.attrs['n_antennas'] = self.n_antennas
            f.attrs['observation_duration'] = self.observation_duration
            f.attrs['file_index'] = file_index
            
            # Store source catalog
            source_group = f.create_group('sources')
            for i, source in enumerate(self.source_catalog):
                source_subgroup = source_group.create_group(f'source_{i:03d}')
                source_subgroup.attrs['ra'] = source['ra']
                source_subgroup.attrs['dec'] = source['dec']
                source_subgroup.attrs['flux'] = source['flux']
                source_subgroup.attrs['name'] = source['name']
    
    def _generate_visibility_data(self, frequencies: np.ndarray, 
                                time_samples: np.ndarray, 
                                file_index: int) -> np.ndarray:
        """Generate realistic visibility data."""
        n_freq = len(frequencies)
        n_time = len(time_samples)
        n_ant = len(self.antenna_positions)
        
        # Initialize visibility array
        # Shape: (n_time, n_freq, n_ant, n_ant, 2) for real/imaginary
        vis_data = np.zeros((n_time, n_freq, n_ant, n_ant, 2), dtype=np.complex64)
        
        # Add noise
        noise_level = 0.01
        vis_data.real = np.random.normal(0, noise_level, vis_data.shape)
        vis_data.imag = np.random.normal(0, noise_level, vis_data.shape)
        
        # Add source contributions
        for source in self.source_catalog:
            # Calculate source position
            source_coord = SkyCoord(ra=source['ra'], dec=source['dec'], unit='deg')
            
            # Add source contribution to visibilities
            for t in range(n_time):
                for f in range(n_freq):
                    # Calculate baseline vectors
                    for i in range(n_ant):
                        for j in range(i+1, n_ant):
                            # Calculate baseline
                            baseline = self.antenna_positions[j] - self.antenna_positions[i]
                            
                            # Calculate UV coordinates
                            u_coord = baseline[0] * frequencies[f] / 3e8
                            v_coord = baseline[1] * frequencies[f] / 3e8
                            
                            # Calculate visibility contribution
                            # Simplified: point source response
                            phase = 2 * np.pi * (u_coord * source_coord.ra.rad + 
                                                v_coord * source_coord.dec.rad)
                            
                            # Add source contribution
                            contribution = source['flux'] * np.exp(1j * phase)
                            vis_data[t, f, i, j, 0] += contribution.real
                            vis_data[t, f, i, j, 1] += contribution.imag
                            
                            # Hermitian symmetry
                            vis_data[t, f, j, i, 0] += contribution.real
                            vis_data[t, f, j, i, 1] -= contribution.imag
        
        return vis_data
    
    def generate_fits_images(self, n_images: int = 3) -> List[str]:
        """
        Generate synthetic FITS images for testing.
        
        Args:
            n_images: Number of FITS images to generate
            
        Returns:
            List of generated FITS file paths
        """
        logger.info(f"Generating {n_images} FITS images")
        
        fits_files = []
        
        for i in range(n_images):
            # Generate filename
            filename = f"test_image_{i:03d}.fits"
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate FITS image
            self._create_fits_image(filepath, i)
            fits_files.append(filepath)
            
            logger.info(f"Generated FITS image: {filename}")
        
        return fits_files
    
    def _create_fits_image(self, filepath: str, image_index: int):
        """Create a single FITS image with realistic data."""
        # Image parameters
        image_size = (512, 512)
        pixel_scale = 3.0  # arcsec per pixel
        center_ra = 180.0
        center_dec = 37.0
        
        # Generate image data
        data = self._generate_image_data(image_size, image_index)
        
        # Create WCS
        wcs = WCS(naxis=2)
        wcs.wcs.crpix = [image_size[0] // 2, image_size[1] // 2]
        wcs.wcs.crval = [center_ra, center_dec]
        wcs.wcs.cdelt = [-pixel_scale / 3600.0, pixel_scale / 3600.0]  # Convert to degrees
        wcs.wcs.ctype = ['RA---SIN', 'DEC--SIN']
        wcs.wcs.cunit = ['deg', 'deg']
        
        # Create header
        header = wcs.to_header()
        header['BUNIT'] = 'Jy/beam'
        header['BMAJ'] = 10.0  # arcsec
        header['BMIN'] = 10.0  # arcsec
        header['BPA'] = 0.0
        header['FREQ'] = 1.4e9  # Hz
        header['CRVAL3'] = 1.4e9
        header['CDELT3'] = 100e6
        header['CTYPE3'] = 'FREQ'
        header['CUNIT3'] = 'Hz'
        
        # Create HDU
        hdu = fits.PrimaryHDU(data, header)
        
        # Write FITS file
        hdu.writeto(filepath, overwrite=True)
    
    def _generate_image_data(self, image_size: Tuple[int, int], 
                           image_index: int) -> np.ndarray:
        """Generate realistic image data."""
        data = np.zeros(image_size)
        
        # Add background noise
        noise_level = 0.01
        data += np.random.normal(0, noise_level, image_size)
        
        # Add sources from catalog
        for source in self.source_catalog:
            # Calculate source position in pixels
            # This is simplified - in practice, you'd use proper coordinate conversion
            source_x = image_size[0] // 2 + (source['ra'] - 180.0) * 3600 / 3.0
            source_y = image_size[1] // 2 + (source['dec'] - 37.0) * 3600 / 3.0
            
            # Check if source is within image bounds
            if 0 <= source_x < image_size[0] and 0 <= source_y < image_size[1]:
                # Add Gaussian source
                sigma = 3.0  # pixels
                y, x = np.ogrid[:image_size[0], :image_size[1]]
                
                # Calculate distance from source
                dist_sq = (x - source_x)**2 + (y - source_y)**2
                
                # Add Gaussian source
                source_data = source['flux'] * np.exp(-dist_sq / (2 * sigma**2))
                data += source_data
        
        # Add some artifacts for testing
        if image_index == 1:
            # Add a bright artifact
            data[100:110, 100:110] += 0.5
        
        return data
    
    def generate_calibration_tables(self) -> List[str]:
        """
        Generate synthetic calibration tables for testing.
        
        Returns:
            List of generated calibration table paths
        """
        logger.info("Generating calibration tables")
        
        # Generate bandpass calibration table
        bcal_table = self._create_bandpass_table()
        
        # Generate gain calibration table
        gcal_table = self._create_gain_table()
        
        return [bcal_table, gcal_table]
    
    def _create_bandpass_table(self) -> str:
        """Create a bandpass calibration table."""
        # This is a simplified implementation
        # In practice, you'd create a proper CASA table
        
        table_path = os.path.join(self.output_dir, "test_bandpass.table")
        
        # Create a simple text file as a placeholder
        with open(table_path, 'w') as f:
            f.write("# Bandpass calibration table\n")
            f.write("# Antenna, Frequency, Amplitude, Phase\n")
            
            for ant in range(self.n_antennas):
                for freq in np.linspace(self.frequency_range[0], self.frequency_range[1], 10):
                    amp = 1.0 + np.random.normal(0, 0.05)
                    phase = np.random.normal(0, 0.1)
                    f.write(f"{ant}, {freq}, {amp}, {phase}\n")
        
        return table_path
    
    def _create_gain_table(self) -> str:
        """Create a gain calibration table."""
        # This is a simplified implementation
        # In practice, you'd create a proper CASA table
        
        table_path = os.path.join(self.output_dir, "test_gain.table")
        
        # Create a simple text file as a placeholder
        with open(table_path, 'w') as f:
            f.write("# Gain calibration table\n")
            f.write("# Antenna, Time, Amplitude, Phase\n")
            
            for ant in range(self.n_antennas):
                for time in np.linspace(0, self.observation_duration, 10):
                    amp = 1.0 + np.random.normal(0, 0.02)
                    phase = np.random.normal(0, 0.05)
                    f.write(f"{ant}, {time}, {amp}, {phase}\n")
        
        return table_path
    
    def generate_mosaic_data(self) -> str:
        """
        Generate synthetic mosaic data for testing.
        
        Returns:
            Path to generated mosaic file
        """
        logger.info("Generating mosaic data")
        
        # Generate multiple FITS images
        image_files = self.generate_fits_images(3)
        
        # Create mosaic file
        mosaic_file = os.path.join(self.output_dir, "test_mosaic.fits")
        
        # For now, just copy the first image as the mosaic
        # In practice, you'd use CASA linearmosaic
        import shutil
        shutil.copy2(image_files[0], mosaic_file)
        
        return mosaic_file
    
    def generate_photometry_data(self) -> str:
        """
        Generate synthetic photometry data for testing.
        
        Returns:
            Path to generated photometry file
        """
        logger.info("Generating photometry data")
        
        # Create photometry table
        photometry_file = os.path.join(self.output_dir, "test_photometry.csv")
        
        # Generate photometry data
        photometry_data = []
        for source in self.source_catalog:
            # Add some noise to the flux
            measured_flux = source['flux'] * (1 + np.random.normal(0, 0.05))
            flux_error = abs(measured_flux * np.random.normal(0, 0.1))
            
            photometry_data.append({
                'source_name': source['name'],
                'ra': source['ra'],
                'dec': source['dec'],
                'flux': measured_flux,
                'flux_error': flux_error,
                'snr': measured_flux / flux_error if flux_error > 0 else 0
            })
        
        # Write CSV file
        with open(photometry_file, 'w') as f:
            f.write("source_name,ra,dec,flux,flux_error,snr\n")
            for data in photometry_data:
                f.write(f"{data['source_name']},{data['ra']},{data['dec']},"
                       f"{data['flux']},{data['flux_error']},{data['snr']}\n")
        
        return photometry_file
    
    def generate_complete_test_dataset(self) -> Dict[str, List[str]]:
        """
        Generate a complete test dataset for comprehensive testing.
        
        Returns:
            Dictionary with all generated test data
        """
        logger.info("Generating complete test dataset")
        
        dataset = {
            'hdf5_files': self.generate_hdf5_files(5),
            'fits_images': self.generate_fits_images(3),
            'calibration_tables': self.generate_calibration_tables(),
            'mosaic_file': [self.generate_mosaic_data()],
            'photometry_file': [self.generate_photometry_data()]
        }
        
        # Create dataset manifest
        manifest_file = os.path.join(self.output_dir, "dataset_manifest.json")
        import json
        
        manifest = {
            'generated_at': Time.now().isot,
            'dataset': dataset,
            'parameters': {
                'frequency_range': self.frequency_range,
                'bandwidth': self.bandwidth,
                'n_channels': self.n_channels,
                'n_antennas': self.n_antennas,
                'observation_duration': self.observation_duration
            }
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Complete test dataset generated in: {self.output_dir}")
        logger.info(f"Dataset manifest: {manifest_file}")
        
        return dataset


# Example usage
if __name__ == "__main__":
    # Create test data generator
    generator = TestDataGenerator()
    
    # Generate complete test dataset
    dataset = generator.generate_complete_test_dataset()
    
    print("Test dataset generated successfully!")
    print(f"Generated files:")
    for category, files in dataset.items():
        print(f"  {category}: {len(files)} files")
        for file in files:
            print(f"    - {file}")
