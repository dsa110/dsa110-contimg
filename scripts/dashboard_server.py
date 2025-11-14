#!/usr/bin/env python3
"""
Simple HTTP server for serving the DSA-110 dashboard with /ui/ base path support.

This server handles the production build which expects to be served from /ui/
by rewriting paths appropriately.
"""

import argparse
import http.server
import os
import socketserver
from pathlib import Path
from urllib.parse import unquote


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that strips /ui/ prefix from paths."""

    def translate_path(self, path):
        """Translate URL path to filesystem path, handling /ui/ prefix.
        
        The production build expects to be served at /ui/, so we:
        1. Strip /ui/ prefix from incoming requests
        2. Serve files from the dist directory
        3. Serve index.html for client-side routing
        """
        # Remove query string
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        
        # Decode percent-encoded characters
        path = unquote(path)
        
        # Strip leading slash
        if path.startswith('/'):
            path = path[1:]
        
        # If path is empty or just "ui" or "ui/", serve index.html
        if not path or path == 'ui' or path == 'ui/':
            path = 'index.html'
        # If path starts with ui/, strip that prefix
        elif path.startswith('ui/'):
            path = path[3:]  # Remove "ui/"
        
        # Convert to filesystem path
        words = path.split('/')
        words = filter(None, words)
        
        # Get the directory we're serving from
        path = self.directory
        for word in words:
            # Security: prevent directory traversal
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        
        return path

    def end_headers(self):
        """Add CORS headers for development."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        super().end_headers()

    def do_GET(self):
        """Handle GET requests with fallback to index.html for client-side routing."""
        # Try to serve the requested file
        path = self.translate_path(self.path)
        
        # If file doesn't exist and doesn't have an extension (likely a route),
        # serve index.html for client-side routing
        if not os.path.exists(path) and '.' not in os.path.basename(self.path):
            self.path = '/index.html'
        
        return super().do_GET()


def serve(port, directory):
    """Start the HTTP server."""
    os.chdir(directory)
    
    with socketserver.TCPServer(("", port), DashboardHTTPRequestHandler) as httpd:
        print(f"Serving DSA-110 Dashboard on port {port}")
        print(f"Serving from: {directory}")
        print(f"Access at: http://localhost:{port}/ui/")
        print(f"Or via root redirect: http://localhost:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve DSA-110 Dashboard")
    parser.add_argument("--port", type=int, default=3210, help="Port to serve on")
    parser.add_argument("--directory", type=str, required=True, help="Directory to serve")
    
    args = parser.parse_args()
    
    # Verify directory exists
    if not Path(args.directory).exists():
        print(f"ERROR: Directory not found: {args.directory}")
        exit(1)
    
    serve(args.port, args.directory)
