#!/usr/bin/env python
"""
Full calibration + imaging pipeline for DSA-110 continuum observations.

Workflow:
1. Query NVSS catalog for bright calibrators in the field
2. Create sky model from NVSS sources
3. Perform bandpass calibration
4. Perform gain calibration (phase + amplitude)
5. Apply calibration solutions
6. Image the field
7. Measure source fluxes

Based on DSA-110 calibration scripts in dsacamera/
"""

import os
import sys
import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.vizier import Vizier
import warnings

# CASA imports
from casatasks import (listobs, flagdata, setjy, ft, gaincal, bandpass, 
                       applycal, tclean, exportfits, split, clearcal)
from casatools import msmetadata, componentlist, image, table

class DSA110CalibrationPipeline:
    """
    Calibration and imaging pipeline for DSA-110.
    """
    
    def __init__(self, ms_path, output_dir='calibrated', verbose=True):
        """
        Initialize pipeline.
        
        Parameters
        ----------
        ms_path : str
            Path to input MS file
        output_dir : str
            Output directory for calibration tables and images
        verbose : bool
            Print progress messages
        """
        self.ms_path = ms_path
        self.output_dir = output_dir
        self.verbose = verbose
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get MS metadata
        self.msmd = msmetadata()
        self.msmd.open(ms_path)
        
        self.field_names = self.msmd.fieldnames()
        self.phase_center = self.msmd.phasecenter(0)  # Field 0
        self.freqs = self.msmd.chanfreqs(0)  # SPW 0
        self.freq_ghz = self.freqs / 1e9
        self.center_freq = (self.freq_ghz[0] + self.freq_ghz[-1]) / 2
        self.bandwidth_mhz = (self.freq_ghz[-1] - self.freq_ghz[0]) * 1000
        
        self.msmd.close()
        
        # Parse phase center
        self.field_center = self._parse_phase_center()
        
        if self.verbose:
            print("="*70)
            print("DSA-110 Calibration Pipeline")
            print("="*70)
            print(f"MS: {ms_path}")
            print(f"Field: {self.field_names[0]}")
            print(f"Center: RA={self.field_center.ra.deg:.4f}°, Dec={self.field_center.dec.deg:.4f}°")
            print(f"Frequency: {self.center_freq:.3f} GHz (BW: {self.bandwidth_mhz:.1f} MHz)")
            print(f"Output: {output_dir}/")
            print("="*70)
            print()
    
    def _parse_phase_center(self):
        """Parse phase center from MS to SkyCoord."""
        # The phase_center dict has 'refer', 'type', 'm0' (RA), 'm1' (Dec)
        ra_rad = self.phase_center['m0']['value']
        dec_rad = self.phase_center['m1']['value']
        return SkyCoord(ra=ra_rad*u.rad, dec=dec_rad*u.rad, frame='icrs')
    
    def query_nvss_sources(self, radius_deg=2.0, min_flux_mjy=10.0, max_sources=100):
        """
        Query NVSS catalog for bright sources in the field.
        
        Parameters
        ----------
        radius_deg : float
            Search radius in degrees
        min_flux_mjy : float
            Minimum flux density in mJy at 1.4 GHz
        max_sources : int
            Maximum number of sources to return
        
        Returns
        -------
        sources : astropy.table.Table
            NVSS sources with RA, Dec, flux
        """
        if self.verbose:
            print("1. Querying NVSS catalog...")
            print(f"   Search center: RA={self.field_center.ra.deg:.4f}°, Dec={self.field_center.dec.deg:.4f}°")
            print(f"   Search radius: {radius_deg}°")
            print(f"   Min flux: {min_flux_mjy} mJy")
        
        # Query Vizier for NVSS sources
        v = Vizier(columns=['*'], row_limit=max_sources)
        v.ROW_LIMIT = max_sources
        
        try:
            result = v.query_region(
                self.field_center,
                radius=radius_deg*u.deg,
                catalog='VIII/65/nvss'  # NVSS catalog
            )
            
            if len(result) == 0:
                print("   ⚠ No NVSS sources found!")
                return None
            
            sources = result[0]
            
            # Filter by flux
            flux_col = 'S1.4'  # 1.4 GHz flux in mJy
            if flux_col in sources.colnames:
                sources = sources[sources[flux_col] > min_flux_mjy]
            
            # Sort by flux (descending)
            if flux_col in sources.colnames:
                sources.sort(flux_col, reverse=True)
            
            if self.verbose:
                print(f"   ✓ Found {len(sources)} sources above {min_flux_mjy} mJy")
                if len(sources) > 0:
                    brightest_flux = sources[flux_col][0] if flux_col in sources.colnames else -1
                    print(f"   Brightest source: {brightest_flux:.1f} mJy")
            
            return sources
            
        except Exception as e:
            print(f"   ⚠ NVSS query failed: {e}")
            return None
    
    def create_sky_model(self, sources, output_cl=None, top_n=50):
        """
        Create CASA component list from NVSS sources.
        
        Parameters
        ----------
        sources : astropy.table.Table
            NVSS sources
        output_cl : str
            Output component list filename
        top_n : int
            Use only top N brightest sources
        
        Returns
        -------
        cl_path : str
            Path to component list
        """
        if output_cl is None:
            output_cl = os.path.join(self.output_dir, 'nvss_skymodel.cl')
        
        if self.verbose:
            print(f"\n2. Creating sky model...")
            print(f"   Using top {top_n} sources")
            print(f"   Output: {output_cl}")
        
        # Remove existing component list
        if os.path.exists(output_cl):
            import shutil
            shutil.rmtree(output_cl)
        
        # Create component list
        cl = componentlist()
        
        # Use top N sources
        sources_to_use = sources[:top_n] if len(sources) > top_n else sources
        
        n_added = 0
        for i, src in enumerate(sources_to_use):
            try:
                # Get coordinates - NVSS returns sexagesimal strings
                ra_str = str(src['RAJ2000']).strip()  # e.g., '18 12 09.58'
                dec_str = str(src['DEJ2000']).strip()  # e.g., '+37 23 41.2'
                flux_mjy = float(src['S1.4'])  # Flux in mJy
                
                # Skip sources with invalid flux
                if not np.isfinite(flux_mjy) or flux_mjy <= 0:
                    if self.verbose:
                        print(f"   ⚠ Skipping source {i+1} with invalid flux")
                    continue
                
                # Parse RA (HH MM SS.SS) and Dec (+DD MM SS.S)
                # Convert to SkyCoord to get proper formatting
                coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg), frame='icrs')
                
                # Format for CASA component list
                direction = f"J2000 {coord.ra.to_string(unit=u.hour, sep=':')} {coord.dec.to_string(unit=u.deg, sep=':')}"
                flux_jy = flux_mjy / 1000.0  # Convert mJy to Jy
                
                # Add point source component
                cl.addcomponent(
                    dir=direction,
                    flux=flux_jy,
                    fluxunit='Jy',
                    freq=f'{self.center_freq}GHz',
                    shape='point',
                    spectrumtype='spectral index',
                    index=-0.7  # Typical spectral index for synchrotron sources
                )
                n_added += 1
                
            except Exception as e:
                if self.verbose:
                    print(f"   ⚠ Error adding source {i+1}: {e}")
                continue
        
        # Save component list
        cl.rename(output_cl)
        cl.close()
        
        if self.verbose:
            print(f"   ✓ Created component list with {n_added} sources")
            if n_added > 0:
                print(f"   Total model flux: {sum(sources_to_use['S1.4'][:n_added])/1000:.2f} Jy")
        
        return output_cl
    
    def flag_data(self):
        """Apply basic flagging (autocorrelations, zeros, shadows)."""
        if self.verbose:
            print("\n3. Flagging data...")
        
        try:
            # Flag autocorrelations
            flagdata(vis=self.ms_path, mode='manual', autocorr=True, 
                    flagbackup=False, action='apply')
            if self.verbose:
                print("   ✓ Flagged autocorrelations")
            
            # Flag zeros
            flagdata(vis=self.ms_path, mode='clip', clipzeros=True,
                    flagbackup=False, action='apply')
            if self.verbose:
                print("   ✓ Flagged zero visibilities")
            
            # Flag shadowed antennas
            flagdata(vis=self.ms_path, mode='shadow', tolerance=0.0,
                    flagbackup=False, action='apply')
            if self.verbose:
                print("   ✓ Flagged shadowed antennas")
            
            return True
            
        except Exception as e:
            print(f"   ⚠ Flagging failed: {e}")
            return False
    
    def set_model(self, cl_path):
        """
        Set MODEL_DATA column using component list.
        
        Parameters
        ----------
        cl_path : str
            Path to component list
        """
        if self.verbose:
            print(f"\n4. Setting model visibilities...")
            print(f"   Component list: {cl_path}")
        
        try:
            # Use ft (Fourier transform) to compute model visibilities
            ft(
                vis=self.ms_path,
                complist=cl_path,
                usescratch=True,  # Create MODEL_DATA column
                incremental=False
            )
            
            if self.verbose:
                print("   ✓ Model visibilities computed")
            
            return True
            
        except Exception as e:
            print(f"   ⚠ Model setting failed: {e}")
            return False
    
    def calibrate(self, refant='', solint_bp='inf', solint_gain='60s'):
        """
        Perform calibration: bandpass then gain.
        
        Parameters
        ----------
        refant : str
            Reference antenna (e.g., 'pad1'). If empty, auto-select.
        solint_bp : str
            Solution interval for bandpass calibration
        solint_gain : str
            Solution interval for gain calibration
        
        Returns
        -------
        bcal_table : str
            Bandpass calibration table
        gcal_table : str
            Gain calibration table
        """
        if self.verbose:
            print(f"\n5. Calibration...")
        
        # Auto-select reference antenna if not specified
        if not refant:
            refant = '1'  # Default to antenna '1' - could be smarter
            if self.verbose:
                print(f"   Reference antenna: {refant} (auto-selected)")
        
        bcal_table = os.path.join(self.output_dir, 'bandpass.bcal')
        gcal_table = os.path.join(self.output_dir, 'gain.gcal')
        
        # Remove existing tables
        for table_path in [bcal_table, gcal_table]:
            if os.path.exists(table_path):
                import shutil
                shutil.rmtree(table_path)
        
        try:
            # Bandpass calibration
            if self.verbose:
                print(f"   Running bandpass calibration (solint={solint_bp})...")
            
            bandpass(
                vis=self.ms_path,
                caltable=bcal_table,
                field='',
                refant=refant,
                solint=solint_bp,
                combine='scan',
                solnorm=False,
                bandtype='B',
                fillgaps=0
            )
            
            if self.verbose:
                print(f"   ✓ Bandpass table: {bcal_table}")
            
            # Gain calibration (phase + amplitude)
            if self.verbose:
                print(f"   Running gain calibration (solint={solint_gain})...")
            
            gaincal(
                vis=self.ms_path,
                caltable=gcal_table,
                field='',
                refant=refant,
                solint=solint_gain,
                gaintype='G',
                calmode='ap',  # Amplitude and phase
                gaintable=[bcal_table],  # Apply bandpass first
                combine='scan'
            )
            
            if self.verbose:
                print(f"   ✓ Gain table: {gcal_table}")
            
            return bcal_table, gcal_table
            
        except Exception as e:
            print(f"   ⚠ Calibration failed: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def apply_calibration(self, bcal_table, gcal_table):
        """
        Apply calibration tables to create CORRECTED_DATA.
        
        Parameters
        ----------
        bcal_table : str
            Bandpass calibration table
        gcal_table : str
            Gain calibration table
        """
        if self.verbose:
            print(f"\n6. Applying calibration...")
        
        try:
            applycal(
                vis=self.ms_path,
                gaintable=[bcal_table, gcal_table],
                interp=['nearest', 'linear'],
                calwt=False,
                flagbackup=False
            )
            
            if self.verbose:
                print("   ✓ Calibration applied to CORRECTED_DATA column")
            
            return True
            
        except Exception as e:
            print(f"   ⚠ Applycal failed: {e}")
            return False
    
    def image(self, imsize=2048, cell='5arcsec', niter=1000, threshold='0.1mJy',
              robust=0.5, datacolumn='corrected'):
        """
        Create calibrated continuum image.
        
        Parameters
        ----------
        imsize : int
            Image size in pixels
        cell : str
            Pixel size
        niter : int
            Number of clean iterations
        threshold : str
            Clean threshold
        robust : float
            Briggs robust parameter
        datacolumn : str
            Data column to image ('data' or 'corrected')
        
        Returns
        -------
        imagename : str
            Base name of output images
        """
        if self.verbose:
            print(f"\n7. Imaging...")
            print(f"   Image size: {imsize}x{imsize} pixels")
            print(f"   Cell size: {cell}")
            print(f"   Clean iterations: {niter}")
            print(f"   Threshold: {threshold}")
            print(f"   Data column: {datacolumn}")
        
        imagename = os.path.join(self.output_dir, 'continuum_image')
        
        try:
            tclean(
                vis=self.ms_path,
                imagename=imagename,
                imsize=imsize,
                cell=cell,
                specmode='mfs',
                deconvolver='hogbom',
                weighting='briggs',
                robust=robust,
                niter=niter,
                threshold=threshold,
                interactive=False,
                nterms=1,
                gridder='standard',
                pblimit=-0.1,
                pbcor=True,  # Primary beam correction
                restoration=True,
                savemodel='none',
                datacolumn=datacolumn,
                parallel=False
            )
            
            if self.verbose:
                print(f"   ✓ Image created: {imagename}.image")
            
            # Export to FITS
            fits_file = imagename + '.fits'
            exportfits(
                imagename=imagename + '.image',
                fitsimage=fits_file,
                overwrite=True,
                dropstokes=True,
                dropdeg=True
            )
            
            if self.verbose:
                print(f"   ✓ FITS exported: {fits_file}")
            
            # Image statistics
            ia = image()
            ia.open(imagename + '.image')
            stats = ia.statistics()
            beam = ia.restoringbeam()
            ia.close()
            
            print("\n" + "="*70)
            print("IMAGE STATISTICS")
            print("="*70)
            print(f"RMS: {stats['rms'][0]*1e3:.2f} mJy/beam")
            print(f"Min: {stats['min'][0]*1e3:.2f} mJy/beam")
            print(f"Max: {stats['max'][0]*1e3:.2f} mJy/beam")
            print(f"Dynamic range: {abs(stats['max'][0]/stats['rms'][0]):.1f}")
            
            if beam:
                print(f"\nSynthesized beam:")
                print(f"  Major axis: {beam['major']['value']:.2f} {beam['major']['unit']}")
                print(f"  Minor axis: {beam['minor']['value']:.2f} {beam['minor']['unit']}")
                print(f"  PA: {beam['positionangle']['value']:.2f} {beam['positionangle']['unit']}")
            print("="*70)
            
            return imagename
            
        except Exception as e:
            print(f"   ⚠ Imaging failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_full_pipeline(self, **kwargs):
        """
        Run the full calibration and imaging pipeline.
        
        Parameters
        ----------
        **kwargs : dict
            Keyword arguments passed to individual steps
        """
        # Step 1: Query NVSS
        sources = self.query_nvss_sources(
            radius_deg=kwargs.get('search_radius', 2.0),
            min_flux_mjy=kwargs.get('min_flux', 10.0),
            max_sources=kwargs.get('max_sources', 100)
        )
        
        if sources is None or len(sources) == 0:
            print("\n❌ No calibrators found. Cannot proceed with calibration.")
            print("   Consider using a different field or relaxing search criteria.")
            return False
        
        # Step 2: Create sky model
        cl_path = self.create_sky_model(sources, top_n=kwargs.get('top_n_sources', 50))
        
        # Step 3: Flag data
        self.flag_data()
        
        # Step 4: Set model
        if not self.set_model(cl_path):
            return False
        
        # Step 5: Calibrate
        bcal, gcal = self.calibrate(
            refant=kwargs.get('refant', ''),
            solint_bp=kwargs.get('solint_bp', 'inf'),
            solint_gain=kwargs.get('solint_gain', '60s')
        )
        
        if bcal is None or gcal is None:
            print("\n❌ Calibration failed. Cannot proceed.")
            return False
        
        # Step 6: Apply calibration
        if not self.apply_calibration(bcal, gcal):
            return False
        
        # Step 7: Image
        imagename = self.image(
            imsize=kwargs.get('imsize', 2048),
            cell=kwargs.get('cell', '5arcsec'),
            niter=kwargs.get('niter', 1000),
            threshold=kwargs.get('threshold', '0.1mJy'),
            robust=kwargs.get('robust', 0.5)
        )
        
        if imagename is None:
            print("\n❌ Imaging failed.")
            return False
        
        print("\n" + "="*70)
        print("✓ PIPELINE COMPLETE!")
        print("="*70)
        print(f"Calibration tables: {self.output_dir}/")
        print(f"Image: {imagename}.image")
        print(f"FITS: {imagename}.fits")
        print("="*70)
        
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='DSA-110 Calibration Pipeline')
    parser.add_argument('ms', help='Input MS file')
    parser.add_argument('-o', '--output', default='calibrated', help='Output directory')
    parser.add_argument('--search-radius', type=float, default=2.0, 
                       help='NVSS search radius (degrees)')
    parser.add_argument('--min-flux', type=float, default=10.0,
                       help='Minimum NVSS flux (mJy)')
    parser.add_argument('--top-n-sources', type=int, default=50,
                       help='Number of brightest sources for calibration')
    parser.add_argument('--refant', default='', help='Reference antenna')
    parser.add_argument('--imsize', type=int, default=2048, help='Image size (pixels)')
    parser.add_argument('--cell', default='5arcsec', help='Pixel size')
    parser.add_argument('--niter', type=int, default=1000, help='Clean iterations')
    parser.add_argument('--threshold', default='0.1mJy', help='Clean threshold')
    
    args = parser.parse_args()
    
    pipeline = DSA110CalibrationPipeline(args.ms, args.output)
    success = pipeline.run_full_pipeline(
        search_radius=args.search_radius,
        min_flux=args.min_flux,
        top_n_sources=args.top_n_sources,
        refant=args.refant,
        imsize=args.imsize,
        cell=args.cell,
        niter=args.niter,
        threshold=args.threshold
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

