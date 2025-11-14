"""
Tests for the dashboard HTTP server with /ui/ base path support.
"""

import http.client
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest


def test_dashboard_server_path_translation():
    """Test that the dashboard server correctly handles /ui/ base path."""
    # Import the dashboard server module
    import sys
    
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    from dashboard_server import DashboardHTTPRequestHandler
    
    # Create a mock request handler
    class MockRequestHandler(DashboardHTTPRequestHandler):
        def __init__(self, directory):
            self.directory = directory
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test files
        (tmpdir_path / "index.html").write_text("<html>index</html>")
        (tmpdir_path / "assets").mkdir()
        (tmpdir_path / "assets" / "test.js").write_text("console.log('test');")
        
        handler = MockRequestHandler(str(tmpdir_path))
        
        # Test path translation
        test_cases = [
            ("/ui/", str(tmpdir_path / "index.html")),
            ("/ui/index.html", str(tmpdir_path / "index.html")),
            ("/ui/assets/test.js", str(tmpdir_path / "assets" / "test.js")),
            ("/", str(tmpdir_path / "index.html")),
        ]
        
        for url_path, expected_fs_path in test_cases:
            result = handler.translate_path(url_path)
            # Normalize paths for comparison
            assert os.path.normpath(result) == os.path.normpath(expected_fs_path), \
                f"Path translation failed for {url_path}: got {result}, expected {expected_fs_path}"


def test_dashboard_server_integration():
    """Integration test: start server and verify it serves files correctly."""
    import sys
    import socketserver
    
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    from dashboard_server import DashboardHTTPRequestHandler
    
    # Create temporary directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create test files
        (tmpdir_path / "index.html").write_text("<html><title>Test Dashboard</title></html>")
        (tmpdir_path / "assets").mkdir()
        (tmpdir_path / "assets" / "app.js").write_text("// test app")
        (tmpdir_path / "js9").mkdir()
        (tmpdir_path / "js9" / "js9Prefs.json").write_text('{"test": true}')
        
        # Start server in a thread
        os.chdir(tmpdir_path)
        port = 9999  # Use high port to avoid conflicts
        
        with socketserver.TCPServer(("", port), DashboardHTTPRequestHandler) as httpd:
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # Wait for server to start
            time.sleep(0.5)
            
            try:
                # Test various endpoints
                conn = http.client.HTTPConnection("localhost", port, timeout=5)
                
                # Test /ui/ -> index.html
                conn.request("GET", "/ui/")
                response = conn.getresponse()
                assert response.status == 200
                content = response.read().decode()
                assert "Test Dashboard" in content
                
                # Test /ui/index.html
                conn.request("GET", "/ui/index.html")
                response = conn.getresponse()
                assert response.status == 200
                
                # Test /ui/assets/app.js
                conn.request("GET", "/ui/assets/app.js")
                response = conn.getresponse()
                assert response.status == 200
                content = response.read().decode()
                assert "test app" in content
                
                # Test /ui/js9/js9Prefs.json
                conn.request("GET", "/ui/js9/js9Prefs.json")
                response = conn.getresponse()
                assert response.status == 200
                content = response.read().decode()
                assert '"test": true' in content
                
                # Test root / -> index.html
                conn.request("GET", "/")
                response = conn.getresponse()
                assert response.status == 200
                content = response.read().decode()
                assert "Test Dashboard" in content
                
                conn.close()
                
            finally:
                httpd.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
