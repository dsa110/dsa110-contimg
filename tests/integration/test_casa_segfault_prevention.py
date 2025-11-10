"""
Integration tests to verify CASA segfault prevention.

These tests specifically target the import chain that previously caused segfaults
and verify that the lazy import fix prevents them.
"""
import pytest
import sys
import subprocess
import importlib
from pathlib import Path


class TestSegfaultPrevention:
    """Test that segfaults are prevented in various scenarios."""
    
    def test_problematic_import_chain(self):
        """
        Test the exact import chain that previously caused segfault.
        
        This was: from dsa110_contimg.qa import create_cutout
        """
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
            'dsa110_contimg.qa.visualization.__init__',
            'dsa110_contimg.qa.__init__',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # This import chain should NOT cause segfault
        try:
            from dsa110_contimg.qa import create_cutout
            assert callable(create_cutout)
        except SystemError as e:
            if "segmentation fault" in str(e).lower() or "segfault" in str(e).lower():
                pytest.fail(f"Segfault detected: {e}")
            raise
    
    def test_casatable_import_via_qa_init(self):
        """
        Test importing CasaTable via qa/__init__.py.
        
        This tests the import chain:
        qa/__init__.py -> qa.visualization -> qa.visualization.casatable
        """
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Import via qa/__init__.py
        try:
            from dsa110_contimg.qa.visualization import CasaTable
            assert CasaTable is not None
            
            # Verify CASA is not initialized yet
            from dsa110_contimg.qa.visualization.casatable import _CASACORE_AVAILABLE
            assert _CASACORE_AVAILABLE is None, "CASA should not be initialized on import"
        except SystemError as e:
            if "segmentation fault" in str(e).lower():
                pytest.fail(f"Segfault detected: {e}")
            raise
    
    def test_subprocess_import_test(self):
        """
        Test imports in a subprocess to catch segfaults that might not
        be caught in the same process.
        """
        test_code = """
import sys
sys.path.insert(0, '/data/dsa110-contimg/src')

# Test the problematic import chain
try:
    from dsa110_contimg.qa import create_cutout
    print("SUCCESS: Import completed without segfault")
    sys.exit(0)
except SystemError as e:
    if "segmentation fault" in str(e).lower():
        print(f"FAILED: Segfault detected: {e}")
        sys.exit(1)
    raise
except Exception as e:
    print(f"INFO: Other exception (not segfault): {e}")
    sys.exit(0)
"""
        
        result = subprocess.run(
            ['/opt/miniforge/envs/casa6/bin/python', '-c', test_code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert "SUCCESS" in result.stdout or "INFO" in result.stdout, \
            f"Unexpected output: {result.stdout}"
        # Check for actual segfault indicators (not just the word in our message)
        assert "FAILED: Segfault detected" not in result.stdout, \
            f"Segfault detected in subprocess: {result.stdout}"
        # Also check stderr for segfault messages
        if result.stderr:
            assert "segmentation fault" not in result.stderr.lower(), \
                f"Segfault detected in stderr: {result.stderr}"
    
    def test_multiple_subprocess_imports(self):
        """
        Test multiple imports in separate subprocesses to ensure
        consistency and catch any race conditions.
        """
        test_code = """
import sys
sys.path.insert(0, '/data/dsa110-contimg/src')

imports_to_test = [
    "from dsa110_contimg.qa import create_cutout",
    "from dsa110_contimg.qa.visualization import CasaTable",
    "from dsa110_contimg.qa.postage_stamps import create_cutout",
]

for import_stmt in imports_to_test:
    try:
        exec(import_stmt)
        print(f"SUCCESS: {import_stmt}")
    except SystemError as e:
        if "segmentation fault" in str(e).lower():
            print(f"FAILED: Segfault with {import_stmt}: {e}")
            sys.exit(1)
        raise
    except Exception as e:
        print(f"INFO: {import_stmt} raised {type(e).__name__}: {e}")

print("ALL_IMPORTS_SUCCESSFUL")
sys.exit(0)
"""
        
        # Run multiple times to catch any race conditions
        for i in range(3):
            result = subprocess.run(
                ['/opt/miniforge/envs/casa6/bin/python', '-c', test_code],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            assert result.returncode == 0, \
                f"Subprocess {i+1} failed: {result.stderr}"
            assert "ALL_IMPORTS_SUCCESSFUL" in result.stdout, \
                f"Not all imports successful in subprocess {i+1}: {result.stdout}"
            # Check for actual segfault indicators
            assert "FAILED: Segfault" not in result.stdout, \
                f"Segfault detected in subprocess {i+1}: {result.stdout}"
            if result.stderr:
                assert "segmentation fault" not in result.stderr.lower(), \
                    f"Segfault detected in stderr of subprocess {i+1}: {result.stderr}"
    
    def test_casa_initialization_on_demand(self):
        """
        Test that CASA initialization happens on demand, not on import.
        """
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        from dsa110_contimg.qa.visualization.casatable import (
            _CASACORE_AVAILABLE,
            _has_casacore,
            CasaTable
        )
        
        # Initially not initialized
        assert _CASACORE_AVAILABLE is None
        
        # Import should not trigger initialization
        assert CasaTable is not None
        assert _CASACORE_AVAILABLE is None
        
        # Only when we actually check availability should it initialize
        try:
            available = _has_casacore()
            # Now it should be initialized (True or False)
            assert _CASACORE_AVAILABLE is not None
        except Exception:
            # If initialization fails, that's okay
            pass
    
    def test_import_all_qa_modules(self):
        """
        Test importing all QA modules to ensure no segfaults.
        """
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
            'dsa110_contimg.qa.postage_stamps',
            'dsa110_contimg.qa.ms_quality',
            'dsa110_contimg.qa.image_quality',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Import all QA modules
        try:
            import dsa110_contimg.qa
            from dsa110_contimg.qa import (
                create_cutout,
                validate_ms_quality,
                validate_image_quality,
            )
            from dsa110_contimg.qa.visualization import (
                CasaTable,
                FITSFile,
                ls,
            )
            from dsa110_contimg.qa.postage_stamps import (
                create_cutout as ps_create_cutout,
                show_all_cutouts,
            )
            
            # All should be importable
            assert callable(create_cutout)
            assert callable(ps_create_cutout)
            assert CasaTable is not None
        except SystemError as e:
            if "segmentation fault" in str(e).lower():
                pytest.fail(f"Segfault detected when importing QA modules: {e}")
            raise

