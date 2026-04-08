#!/usr/bin/env python3
"""
Simple HTTP Server for Static Site Testing
Serves the generated static site locally with proper MIME types
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

class StaticHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="docs", **kwargs)
    
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_POST(self):
        # Handle POST requests for forms (simulate success)
        if self.path == '/login.html' or self.path == '/login':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Redirect to index.html after "login"
            self.wfile.write(b'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Login Redirect</title>
                    <meta http-equiv="refresh" content="1; url=index.html">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .message { background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px; }
                    </style>
                </head>
                <body>
                    <div class="message">
                        <h2>Login Successful!</h2>
                        <p>Redirecting to dashboard...</p>
                        <p><a href="index.html">Click here if not redirected</a></p>
                    </div>
                </body>
                </html>
            ''')
        else:
            self.send_error(404, "File not found")
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def serve_static(port=8000):
    """Serve static files from docs directory"""
    
    # Change to docs directory
    docs_dir = Path(__file__).parent / 'docs'
    if not docs_dir.exists():
        print("❌ docs directory not found. Run 'python freeze_flask_app.py' first.")
        return
    
    os.chdir(docs_dir)
    
    try:
        with socketserver.TCPServer(("", port), StaticHTTPRequestHandler) as httpd:
            print(f"🚀 Static Server Running")
            print(f"📍 URL: http://localhost:{port}")
            print(f"📁 Directory: {docs_dir.absolute()}")
            print(f"⏹️  Press CTRL+C to stop")
            print()
            print("🌐 Available Pages:")
            print("   http://localhost:{}/index.html - Dashboard")
            print("   http://localhost:{}/login.html - Login")
            print("   http://localhost:{}/upload.html - Upload")
            print("   http://localhost:{}/about.html - About")
            print("   http://localhost:{}/reports.html - Reports")
            print("   http://localhost:{}/admin.html - Admin")
            print()
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"   python serve_static.py --port {port + 1}")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Serve static site locally')
    parser.add_argument('--port', type=int, default=8000, help='Port number (default: 8000)')
    
    args = parser.parse_args()
    
    serve_static(args.port)
