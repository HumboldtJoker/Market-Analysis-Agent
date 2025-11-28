"""
AutoInvestor Desktop Launcher
Creates a native window with embedded web view running the Flask backend
"""

import os
import sys
import threading
import time
import socket

# Add parent and current directory to path
DESKTOP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DESKTOP_DIR)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, DESKTOP_DIR)


def find_free_port():
    """Find an available port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        
        return s.getsockname()[1]


def wait_for_server(port, timeout=10):
    """Wait for the Flask server to start"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', port))
                return True
        except ConnectionRefusedError:
            time.sleep(0.1)
    return False


def run_flask(port):
    """Run Flask in a background thread"""
    from app import app
    # Suppress Flask startup messages
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def main():
    """Main entry point"""
    try:
        import webview
    except ImportError:
        print("PyWebView not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pywebview'])
        import webview

    # Find available port
    port = find_free_port()
    print(f"Starting server on port {port}...")

    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    flask_thread.start()

    # Wait for server to be ready
    if not wait_for_server(port):
        print("Error: Server failed to start")
        return

    print("Server ready, launching window...")

    # Create native window
    window = webview.create_window(
        title='AutoInvestor - AI Investment Research',
        url=f'http://127.0.0.1:{port}/',
        width=1200,
        height=800,
        resizable=True,
        min_size=(800, 600),
        text_select=True
    )

    # Start the webview (this blocks until window is closed)
    webview.start(debug=False)

    print("Window closed, shutting down...")


if __name__ == '__main__':
    main()
