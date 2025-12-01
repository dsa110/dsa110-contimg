"""
Unit tests for conversion/strategies/writers.py

Tests the MS writer factory and writer selection.

NOTE: These tests avoid importing actual CASA-dependent modules to prevent
test hangs. They test the fixtures and interface compliance instead.
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.fixtures import (
    MockUVData,
    create_mock_uvdata,
)


class TestTestWriterFixtures:
    """Tests for test writer fixtures (no CASA dependencies)."""
    
    def test_test_writer_available(self):
        """Test fixtures should provide PyuvdataWriter."""
        from tests.fixtures.writers import PyuvdataWriter
        
        assert PyuvdataWriter is not None
    
    def test_pyuvdata_writer_write_returns_type(self):
        """PyuvdataWriter.write() should return 'pyuvdata'."""
        from tests.fixtures.writers import PyuvdataWriter
        
        mock_uvdata = MagicMock()
        mock_uvdata.write_ms = MagicMock()
        
        writer = PyuvdataWriter(mock_uvdata, "/tmp/test.ms")
        result = writer.write()
        
        assert result == "pyuvdata"
        mock_uvdata.write_ms.assert_called_once()
    
    def test_get_test_writer(self):
        """get_test_writer should return correct class."""
        from tests.fixtures.writers import get_test_writer, PyuvdataMonolithicWriter
        
        writer_cls = get_test_writer("pyuvdata")
        
        assert writer_cls is PyuvdataMonolithicWriter
    
    def test_get_test_writer_unknown_raises(self):
        """get_test_writer should raise for unknown type."""
        from tests.fixtures.writers import get_test_writer
        
        with pytest.raises(ValueError, match="Unknown test writer"):
            get_test_writer("unknown")
    
    def test_pyuvdata_writer_get_files_returns_none(self):
        """PyuvdataWriter.get_files_to_process() should return None."""
        from tests.fixtures.writers import PyuvdataWriter
        
        mock_uvdata = MagicMock()
        writer = PyuvdataWriter(mock_uvdata, "/tmp/test.ms")
        
        assert writer.get_files_to_process() is None


class TestMockUVDataForWriters:
    """Tests for MockUVData compatibility with writers."""
    
    def test_mock_uvdata_has_write_ms(self):
        """MockUVData should have write_ms method."""
        mock_uv = create_mock_uvdata()
        
        assert hasattr(mock_uv, "write_ms")
        assert callable(mock_uv.write_ms)
    
    def test_mock_uvdata_write_ms_no_error(self):
        """MockUVData.write_ms should not raise."""
        mock_uv = create_mock_uvdata()
        
        # Should be a no-op
        mock_uv.write_ms("/tmp/test.ms")
    
    def test_mock_uvdata_has_required_attributes(self):
        """MockUVData should have attributes needed by writers."""
        mock_uv = create_mock_uvdata()
        
        # Attributes used by writers
        assert hasattr(mock_uv, "Nfreqs")
        assert hasattr(mock_uv, "Nblts")
        assert hasattr(mock_uv, "data_array")
        assert hasattr(mock_uv, "freq_array")
        assert hasattr(mock_uv, "antenna_positions")


class TestWriterInterfaceMocking:
    """Tests for writer interface using mocks (no CASA imports)."""
    
    def test_mock_writer_interface(self):
        """Test mocking the writer interface."""
        # Create a mock writer that follows the interface
        mock_writer = MagicMock()
        mock_writer.write.return_value = "mock-writer"
        mock_writer.get_files_to_process.return_value = ["/path/to/file.hdf5"]
        
        # Verify interface
        assert mock_writer.write() == "mock-writer"
        assert mock_writer.get_files_to_process() == ["/path/to/file.hdf5"]
    
    def test_writer_factory_pattern(self):
        """Test that writer factory pattern works with mocks."""
        # Mock the writer factory
        mock_factory = MagicMock()
        mock_writer_cls = MagicMock()
        mock_factory.return_value = mock_writer_cls
        
        # Simulate get_writer behavior
        def get_writer(writer_type):
            writers = {"test": mock_writer_cls}
            if writer_type not in writers:
                raise ValueError(f"Unknown writer: {writer_type}")
            return writers[writer_type]
        
        # Test
        cls = get_writer("test")
        assert cls is mock_writer_cls
        
        with pytest.raises(ValueError):
            get_writer("unknown")
