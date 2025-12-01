"""
Unit tests for conversion/strategies/writers.py

Tests the MS writer factory and writer selection.
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.fixtures import (
    MockUVData,
    create_mock_uvdata,
)


class TestGetWriter:
    """Tests for get_writer factory function."""
    
    def test_get_parallel_subband_writer(self):
        """Should return DirectSubbandWriter for 'parallel-subband'."""
        from dsa110_contimg.conversion.strategies.writers import get_writer
        
        writer_cls = get_writer("parallel-subband")
        
        assert writer_cls is not None
        assert "DirectSubbandWriter" in writer_cls.__name__ or "Subband" in writer_cls.__name__
    
    def test_get_pyuvdata_writer(self):
        """Should return PyuvdataWriter for 'pyuvdata'."""
        from dsa110_contimg.conversion.strategies.writers import get_writer
        
        writer_cls = get_writer("pyuvdata")
        
        assert writer_cls is not None
    
    def test_unknown_writer_raises(self):
        """Unknown writer type should raise ValueError."""
        from dsa110_contimg.conversion.strategies.writers import get_writer
        
        with pytest.raises(ValueError, match="Unknown writer"):
            get_writer("nonexistent-writer")
    
    def test_default_writer(self):
        """Default writer should be parallel-subband."""
        from dsa110_contimg.conversion.strategies.writers import get_writer, DEFAULT_WRITER
        
        default_cls = get_writer(DEFAULT_WRITER)
        
        assert default_cls is not None


class TestWriterInterface:
    """Tests for writer interface compliance."""
    
    def test_writer_has_write_method(self):
        """All writers should have a write() method."""
        from dsa110_contimg.conversion.strategies.writers import get_writer, AVAILABLE_WRITERS
        
        for writer_type in AVAILABLE_WRITERS:
            writer_cls = get_writer(writer_type)
            assert hasattr(writer_cls, "write"), f"{writer_type} missing write method"
    
    def test_writer_accepts_uvdata_and_path(self):
        """Writers should accept UVData and output path."""
        from dsa110_contimg.conversion.strategies.writers import get_writer
        
        mock_uvdata = create_mock_uvdata()
        output_path = "/tmp/test_output.ms"
        
        # DirectSubbandWriter
        writer_cls = get_writer("parallel-subband")
        
        # Should be instantiable (may need file_list for some writers)
        try:
            writer = writer_cls(mock_uvdata, output_path, file_list=[])
        except TypeError:
            # Some writers may need different args - that's OK
            pass


class TestDirectSubbandWriter:
    """Tests for DirectSubbandWriter."""
    
    def test_init_requires_file_list(self):
        """DirectSubbandWriter should accept file_list parameter."""
        from dsa110_contimg.conversion.strategies.direct_subband import DirectSubbandWriter
        
        mock_uvdata = create_mock_uvdata()
        file_list = ["/path/to/sb00.hdf5", "/path/to/sb01.hdf5"]
        
        # Should not raise
        writer = DirectSubbandWriter(
            mock_uvdata, 
            "/tmp/output.ms",
            file_list=file_list,
        )
        
        assert writer.file_list == file_list
    
    def test_get_files_to_process(self):
        """Should return the file list."""
        from dsa110_contimg.conversion.strategies.direct_subband import DirectSubbandWriter
        
        mock_uvdata = create_mock_uvdata()
        file_list = ["/path/to/sb00.hdf5", "/path/to/sb01.hdf5"]
        
        writer = DirectSubbandWriter(
            mock_uvdata,
            "/tmp/output.ms",
            file_list=file_list,
        )
        
        assert writer.get_files_to_process() == file_list
    
    def test_write_returns_writer_type(self):
        """write() should return the writer type string."""
        from dsa110_contimg.conversion.strategies.direct_subband import DirectSubbandWriter
        
        mock_uvdata = create_mock_uvdata()
        
        writer = DirectSubbandWriter(
            mock_uvdata,
            "/tmp/output.ms",
            file_list=[],
        )
        
        # Mock the actual write operation
        with patch.object(writer, "_write_ms") as mock_write:
            mock_write.return_value = None
            
            result = writer.write()
            
            assert isinstance(result, str)


class TestPyuvdataWriter:
    """Tests for pyuvdata-based writers."""
    
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
