"""
Security tests for path validation utilities.

Tests that path validation correctly prevents path traversal attacks.
"""

import pytest

from dsa110_contimg.utils.path_validation import (
    get_safe_path,
    is_safe_path,
    sanitize_filename,
    validate_path,
)


class TestPathValidation:
    """Test path validation security."""

    def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        # These should all raise ValueError
        malicious_paths = [
            "../../etc/passwd",
            "..\\..\\etc\\passwd",
            "../etc/passwd",
            "../../../etc/passwd",
            "base/../../../etc/passwd",
            "/etc/passwd",
            "base/../../etc/passwd",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises(ValueError, match="path traversal|escape"):
                validate_path(malicious_path, base_dir)

    def test_safe_paths_allowed(self, tmp_path):
        """Test that safe paths within base directory are allowed."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        (base_dir / "subdir").mkdir()
        (base_dir / "subdir" / "file.txt").touch()

        # These should all work
        safe_paths = [
            "subdir",
            "subdir/file.txt",
            "file.txt",
        ]

        for safe_path in safe_paths:
            result = validate_path(safe_path, base_dir)
            assert result.exists() or result.parent.exists()

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Dangerous characters should raise ValueError
        dangerous_names = [
            "../../etc/passwd",
            "file/name.txt",
            "file\\name.txt",
            "file..txt",
            "\x00file.txt",
        ]

        for dangerous_name in dangerous_names:
            with pytest.raises(ValueError):
                sanitize_filename(dangerous_name)

        # Safe filenames should work
        safe_names = [
            "file.txt",
            "image_123.fits",
            "test-file-name.png",
        ]

        for safe_name in safe_names:
            result = sanitize_filename(safe_name)
            assert result == safe_name.strip().strip(".")

    def test_get_safe_path(self, tmp_path):
        """Test get_safe_path convenience function."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        # Safe path should work
        safe_path = get_safe_path("subdir", base_dir, "user_data")
        assert safe_path.parent == base_dir / "user_data"

        # Path traversal should fail
        with pytest.raises(ValueError):
            get_safe_path("../../../etc/passwd", base_dir)

    def test_is_safe_path(self, tmp_path):
        """Test is_safe_path checker."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        (base_dir / "safe_file.txt").touch()

        # Safe paths
        assert is_safe_path("safe_file.txt", [base_dir])
        assert is_safe_path(base_dir / "safe_file.txt", [base_dir])

        # Unsafe paths
        assert not is_safe_path("../../../etc/passwd", [base_dir])
        assert not is_safe_path("/etc/passwd", [base_dir])

    def test_absolute_path_handling(self, tmp_path):
        """Test handling of absolute paths."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        # Absolute path within base should work if allow_absolute=True
        abs_path = base_dir / "file.txt"
        abs_path.touch()
        result = validate_path(str(abs_path), base_dir, allow_absolute=True)
        assert result == abs_path.resolve()

        # Absolute path outside base should fail
        outside_path = tmp_path / "outside" / "file.txt"
        outside_path.parent.mkdir()
        outside_path.touch()
        with pytest.raises(ValueError):
            validate_path(str(outside_path), base_dir, allow_absolute=True)

    def test_symlink_handling(self, tmp_path):
        """Test that symlinks don't bypass validation."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        (base_dir / "safe").mkdir()

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").touch()

        # Create symlink inside base pointing outside
        symlink_path = base_dir / "safe" / "link"
        symlink_path.symlink_to(outside_dir)

        # Accessing via symlink should still be validated
        # The validate_path should catch this
        try:
            result = validate_path("safe/link/secret.txt", base_dir)
            # If it doesn't raise, the resolved path should still be within base
            assert str(result.resolve()).startswith(str(base_dir.resolve()))
        except ValueError:
            # This is also acceptable - validation caught the issue
            pass
