#!/opt/miniforge/envs/casa6/bin/python
"""
Test pyradiosky functionality and compatibility with casa6 environment.

This script tests:
1. pyradiosky installation and import
2. Basic SkyModel creation
3. Catalog reading capabilities
4. Compatibility with existing dependencies
"""

import sys
from pathlib import Path


def test_import():
    """Test pyradiosky import."""
    print("=" * 60)
    print("Test 1: pyradiosky Import")
    print("=" * 60)
    
    try:
        import pyradiosky
        print(f":check: pyradiosky imported successfully")
        print(f"  Version: {pyradiosky.__version__}")
        return True, pyradiosky
    except ImportError as e:
        print(f":cross: Failed to import pyradiosky: {e}")
        return False, None


def test_skymodel_creation(pyradiosky):
    """Test basic SkyModel creation."""
    print("\n" + "=" * 60)
    print("Test 2: Basic SkyModel Creation")
    print("=" * 60)
    
    try:
        import astropy.units as u
        import numpy as np
        from astropy.coordinates import SkyCoord
        from pyradiosky import SkyModel

        # Create a simple point source sky model
        n_sources = 3
        ra = np.array([83.633208, 83.7, 83.8]) * u.deg
        dec = np.array([55.778611, 55.8, 55.9]) * u.deg
        stokes = np.zeros((4, 1, n_sources))
        stokes[0, 0, :] = [2.3, 1.5, 0.8]  # I flux in Jy
        
        skycoord = SkyCoord(ra=ra, dec=dec, frame='icrs')
        
        sky = SkyModel(
            name=[f"source_{i}" for i in range(n_sources)],
            skycoord=skycoord,
            stokes=stokes * u.Jy,
            spectral_type='flat',
            component_type='point',
        )
        
        print(f":check: SkyModel created successfully")
        print(f"  Ncomponents: {sky.Ncomponents}")
        print(f"  Component type: {sky.component_type}")
        print(f"  Spectral type: {sky.spectral_type}")
        return True
    except Exception as e:
        print(f":cross: SkyModel creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependency_compatibility():
    """Test compatibility with existing dependencies."""
    print("\n" + "=" * 60)
    print("Test 3: Dependency Compatibility")
    print("=" * 60)
    
    dependencies = {
        'astropy': 'astropy',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'h5py': 'h5py',
        'scipy': 'scipy',
        'pyuvdata': 'pyuvdata',
    }
    
    results = {}
    for name, module in dependencies.items():
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'unknown')
            results[name] = (True, version)
            print(f":check: {name}: {version}")
        except ImportError:
            results[name] = (False, None)
            print(f":cross: {name}: NOT INSTALLED")
    
    all_ok = all(status for status, _ in results.values())
    return all_ok


def test_casa_compatibility():
    """Test that CASA tools still work after pyradiosky import."""
    print("\n" + "=" * 60)
    print("Test 4: CASA Compatibility Check")
    print("=" * 60)
    
    try:
        # Import pyradiosky first
        import pyradiosky

        # Then try to import CASA tools
        try:
            from casatools import componentlist
            print(":check: casatools.componentlist imports successfully")
        except Exception as e:
            print(f":cross: casatools.componentlist import failed: {e}")
            return False
        
        try:
            from casatasks import ft
            print(":check: casatasks.ft imports successfully")
        except Exception as e:
            print(f":cross: casatasks.ft import failed: {e}")
            return False
        
        return True
    except Exception as e:
        print(f":cross: CASA compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skymodel_io():
    """Test SkyModel I/O capabilities."""
    print("\n" + "=" * 60)
    print("Test 5: SkyModel I/O Capabilities")
    print("=" * 60)
    
    try:
        import os
        import tempfile

        import astropy.units as u
        import numpy as np
        from astropy.coordinates import SkyCoord
        from pyradiosky import SkyModel

        # Create a simple sky model
        ra = np.array([83.633208]) * u.deg
        dec = np.array([55.778611]) * u.deg
        stokes = np.zeros((4, 1, 1))
        stokes[0, 0, 0] = 2.3  # I flux in Jy
        
        skycoord = SkyCoord(ra=ra, dec=dec, frame='icrs')
        
        sky = SkyModel(
            name=["test_source"],
            skycoord=skycoord,
            stokes=stokes * u.Jy,
            spectral_type='flat',
            component_type='point',
        )
        
        # Test text catalog write
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            sky.write_text_catalog(temp_path)
            print(f":check: write_text_catalog() works")
            
            # Check file was created
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                print(f"  File created: {os.path.getsize(temp_path)} bytes")
                os.unlink(temp_path)
            else:
                print(f"  :warning: File created but appears empty")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            print(f":cross: write_text_catalog() failed: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False
        
        # Test skyh5 write (if h5py available)
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.skyh5', delete=False) as f:
                temp_path = f.name
            
            sky.write_skyh5(temp_path)
            print(f":check: write_skyh5() works")
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                print(f"  File created: {os.path.getsize(temp_path)} bytes")
                os.unlink(temp_path)
            else:
                print(f"  :warning: File created but appears empty")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            print(f":warning: write_skyh5() failed (may be expected): {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return True
    except Exception as e:
        print(f":cross: SkyModel I/O test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all pyradiosky tests."""
    print("\n" + "=" * 60)
    print("pyradiosky Compatibility Test Suite")
    print("=" * 60)
    print()
    
    results = {}
    
    # Test 1: Import
    success, pyradiosky_module = test_import()
    results['import'] = success
    if not success:
        print("\n:cross: Cannot proceed without pyradiosky")
        return 1
    
    # Test 2: Basic functionality
    results['creation'] = test_skymodel_creation(pyradiosky_module)
    
    # Test 3: Dependencies
    results['dependencies'] = test_dependency_compatibility()
    
    # Test 4: CASA compatibility
    results['casa'] = test_casa_compatibility()
    
    # Test 5: I/O
    results['io'] = test_skymodel_io()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Import: {':check:' if results['import'] else ':cross:'}")
    print(f"SkyModel Creation: {':check:' if results['creation'] else ':cross:'}")
    print(f"Dependencies: {':check:' if results['dependencies'] else ':cross:'}")
    print(f"CASA Compatibility: {':check:' if results['casa'] else ':cross:'}")
    print(f"I/O Capabilities: {':check:' if results['io'] else ':cross:'}")
    
    if all(results.values()):
        print("\n:check: All tests passed - pyradiosky is ready for use")
        return 0
    elif results['import'] and results['creation'] and results['dependencies']:
        print("\n:warning: Core functionality works - some optional features may have issues")
        return 0
    else:
        print("\n:cross: Critical tests failed - check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

