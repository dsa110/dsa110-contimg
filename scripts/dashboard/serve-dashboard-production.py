#!/opt/miniforge/envs/casa6/bin/python
"""
Production Dashboard HTTP Server
Serves the frontend build with proper /ui/ base path handling and SPA routing
"""

import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlparse

# Get build directory and port
BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
PORT = int(os.environ.get("CONTIMG_DASHBOARD_PORT", "3210"))
BASE_PATH = "/ui"


class DashboardHandler(BaseHTTPRequestHandler):
    def _serve_file(self, file_path):
        """Serve a file with proper headers"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                if file_path.endswith(".js"):
                    content_type = "application/javascript"
                elif file_path.endswith(".css"):
                    content_type = "text/css"
                elif file_path.endswith(".html"):
                    content_type = "text/html"
                elif file_path.endswith(".json"):
                    content_type = "application/json"
                elif file_path.endswith(".wasm"):
                    content_type = "application/wasm"
                elif file_path.endswith(".svg"):
                    content_type = "image/svg+xml"
                else:
                    content_type = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            # Add CORS headers
            self.send_header("Access-Control-Allow-Origin", "*")
            # Cache control for assets
            if "/assets/" in self.path:
                self.send_header("Cache-Control", "public, max-age=31536000")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "File not found")
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_GET(self):
        """Handle GET requests with /ui/ base path and SPA routing"""
        self._handle_request()

    def do_HEAD(self):
        """Handle HEAD requests (for asset preflight checks)"""
        self._handle_request(head_only=True)

    def _handle_request(self, head_only=False):
        """Common request handler for GET and HEAD"""
        parsed_path = urlparse(self.path)
        path = unquote(parsed_path.path)

        # Remove base path if present
        if path.startswith(BASE_PATH):
            path = path[len(BASE_PATH) :]

        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        # Handle root - serve index.html
        if path == "/":
            path = "/index.html"

        # Build full file path
        file_path = os.path.join(BUILD_DIR, path.lstrip("/"))

        # For SPA routing: if file doesn't exist and it's not an asset, serve index.html
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            # Check if it's an asset request
            if path.startswith("/assets/") or "." in os.path.basename(path):
                # Asset not found
                self.send_error(404, "File not found")
                return
            else:
                # SPA route - serve index.html
                file_path = os.path.join(BUILD_DIR, "index.html")

        # Serve the file
        if head_only:
            # For HEAD, just send headers
            try:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    content_type, _ = mimetypes.guess_type(file_path)
                    if content_type is None:
                        if file_path.endswith(".js"):
                            content_type = "application/javascript"
                        elif file_path.endswith(".css"):
                            content_type = "text/css"
                        elif file_path.endswith(".html"):
                            content_type = "text/html"
                        else:
                            content_type = "application/octet-stream"

                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(size))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                else:
                    self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, f"Server error: {str(e)}")
        else:
            self._serve_file(file_path)

    def log_message(self, format, *args):
        """Override to suppress default logging"""
        # Only log errors
        if args[1].startswith("4") or args[1].startswith("5"):
            super().log_message(format, *args)


def main():
    """Start the HTTP server"""
    if not os.path.exists(BUILD_DIR):
        print(f"ERROR: Build directory not found: {BUILD_DIR}", file=sys.stderr)
        print("Run build-dashboard-production.sh first", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(os.path.join(BUILD_DIR, "index.html")):
        print(f"ERROR: index.html not found in {BUILD_DIR}", file=sys.stderr)
        sys.exit(1)

    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, DashboardHandler)

    print(f"Serving DSA-110 Dashboard on port {PORT}")
    print(f"Serving from: {BUILD_DIR}")
    print(f"Base path: {BASE_PATH}")
    print(f"Access at: http://localhost:{PORT}{BASE_PATH}/")
    print("Press Ctrl+C to stop")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    main()
