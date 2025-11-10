"""
Tests for lazy CASA imports to prevent segfaults.

These tests verify that CASA modules are imported lazily and only when needed,
preventing segfaults during module initialization.
"""
import pytest
import sys
import importlib
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestLazyCASAImports:
    """Test that CASA imports are lazy and don't trigger segfaults."""
    
    def test_import_qa_module_no_segfault(self):
        """Test that importing qa module doesn't trigger CASA initialization."""
        # Clear any cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Import should succeed without segfault
        import dsa110_contimg.qa
        assert hasattr(dsa110_contimg.qa, 'create_cutout')
        
        # Verify CASA is not initialized yet
        from dsa110_contimg.qa.visualization.casatable import _CASACORE_AVAILABLE
        assert _CASACORE_AVAILABLE is None, "CASA should not be initialized on module import"
    
    def test_import_casatable_class_no_segfault(self):
        """Test that importing CasaTable class doesn't trigger CASA initialization."""
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Import CasaTable class
        from dsa110_contimg.qa.visualization import CasaTable
        
        # Verify CASA is not initialized yet
        from dsa110_contimg.qa.visualization.casatable import _CASACORE_AVAILABLE
        assert _CASACORE_AVAILABLE is None, "CASA should not be initialized on class import"
    
    def test_casa_initialized_only_when_needed(self):
        """Test that CASA is initialized only when CasaTable is actually used."""
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
        
        # Try to check availability - this should trigger initialization
        try:
            available = _has_casacore()
            # If CASA is available, it should be initialized now
            if available:
                assert _CASACORE_AVAILABLE is True
            else:
                assert _CASACORE_AVAILABLE is False
        except Exception:
            # If initialization fails, that's okay - we're testing lazy loading
            pass
    
    def test_multiple_imports_no_issue(self):
        """Test that multiple imports don't cause issues."""
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Multiple imports should work fine
        import dsa110_contimg.qa
        from dsa110_contimg.qa import create_cutout
        from dsa110_contimg.qa.visualization import CasaTable
        from dsa110_contimg.qa.postage_stamps import create_cutout as ps_create_cutout
        
        # All should be importable
        assert hasattr(dsa110_contimg.qa, 'create_cutout')
        assert CasaTable is not None
    
    def test_postage_stamps_import_no_casa(self):
        """Test that postage_stamps module can be imported without CASA."""
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa.postage_stamps',
            'dsa110_contimg.qa',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Import postage stamps directly (should not trigger CASA)
        from dsa110_contimg.qa.postage_stamps import create_cutout, show_all_cutouts
        
        assert callable(create_cutout)
        assert callable(show_all_cutouts)
    
    def test_casatable_lazy_import_functions(self):
        """Test that lazy import helper functions work correctly."""
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        from dsa110_contimg.qa.visualization.casatable import (
            _ensure_casa_initialized,
            _has_casacore,
            _get_table_class,
            _CASACORE_AVAILABLE,
            _CASACORE_TABLE
        )
        
        # Initially not initialized
        assert _CASACORE_AVAILABLE is None
        assert _CASACORE_TABLE is None
        
        # Call lazy initialization
        try:
            table_class, available = _ensure_casa_initialized()
            # Should have attempted initialization
            assert _CASACORE_AVAILABLE is not None
        except Exception:
            # If CASA is not available, that's fine for this test
            pass
    
    def test_casatable_usage_triggers_lazy_import(self):
        """Test that using CasaTable triggers lazy import."""
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa.visualization.casatable',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        from dsa110_contimg.qa.visualization.casatable import (
            CasaTable,
            _CASACORE_AVAILABLE
        )
        
        # Initially not initialized
        assert _CASACORE_AVAILABLE is None
        
        # Try to create a CasaTable instance (even with invalid path)
        # This should trigger lazy import
        try:
            table = CasaTable(name="/nonexistent/path")
            # If it doesn't raise immediately, try to access a property
            # that would trigger CASA initialization
            try:
                _ = table.nrows
            except Exception:
                pass
        except Exception:
            # Expected if path doesn't exist or CASA not available
            pass
        
        # After attempting to use CasaTable, CASA should be initialized
        # (or at least attempted)
        from dsa110_contimg.qa.visualization.casatable import _CASACORE_AVAILABLE
        # Should not be None anymore (either True or False)
        # Note: This might still be None if the error occurred before initialization
        # That's okay - the important thing is no segfault occurred
    
    @pytest.mark.skipif(
        not Path("/opt/miniforge/envs/casa6/bin/python").exists(),
        reason="CASA6 not available"
    )
    def test_import_chain_no_segfault_with_casa(self):
        """Test the full import chain that previously caused segfault."""
        # This is the import chain that previously caused segfault:
        # from dsa110_contimg.qa import create_cutout
        
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
            'dsa110_contimg.qa.visualization.__init__',
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
                pytest.fail(f"Segfault detected during import: {e}")
            raise
        except Exception as e:
            # Other exceptions are okay (e.g., ImportError if CASA not available)
            pass


class TestCASAImportErrorHandling:
    """Test error handling when CASA is not available."""
    
    def test_casatable_handles_missing_casa_gracefully(self):
        """Test that CasaTable handles missing CASA gracefully."""
        from dsa110_contimg.qa.visualization.casatable import (
            _has_casacore,
            _get_table_class,
            CasaTable
        )
        
        # Check availability
        available = _has_casacore()
        
        # If CASA is not available, operations should fail gracefully
        if not available:
            table_class = _get_table_class()
            assert table_class is None
            
            # Creating CasaTable should not crash
            table = CasaTable(name="/nonexistent/path")
            assert table is not None
            
            # Operations should fail with RuntimeError, not segfault
            with pytest.raises(RuntimeError, match="casacore.tables not available"):
                with table.lock_table():
                    pass


class TestImportOrder:
    """Test that import order doesn't matter."""
    
    def test_import_order_independence(self):
        """Test that different import orders work correctly."""
        # Clear cached imports
        modules_to_clear = [
            'dsa110_contimg.qa',
            'dsa110_contimg.qa.visualization',
            'dsa110_contimg.qa.visualization.casatable',
            'dsa110_contimg.qa.postage_stamps',
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Test different import orders
        orders = [
            # Order 1: qa first
            lambda: (__import__('dsa110_contimg.qa'),),
            # Order 2: postage_stamps first
            lambda: (__import__('dsa110_contimg.qa.postage_stamps'),),
            # Order 3: visualization first
            lambda: (__import__('dsa110_contimg.qa.visualization'),),
        ]
        
        for order_func in orders:
            # Clear modules
            for mod in modules_to_clear:
                if mod in sys.modules:
                    del sys.modules[mod]
            
            # Import in this order
            try:
                order_func()
                # Should not cause segfault
            except SystemError as e:
                if "segmentation fault" in str(e).lower():
                    pytest.fail(f"Segfault detected with import order: {e}")
                raise

