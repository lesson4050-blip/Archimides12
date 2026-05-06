import uvicorn
import os
import sys
import io

# Force UTF-8 for everything
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import socket
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except socket.error:
            return False

if __name__ == "__main__":
    port = 8001
    if not check_port(port):
        print(f"ERROR: Port {port} is already in use!")
        print(f"Please kill the process using 'netstat -ano | findstr :{port}' and then 'taskkill /F /PID <PID>'")
        sys.exit(1)

    # Ensure workspace exists
    os.makedirs("./workspace", exist_ok=True)
    
    # Run FastAPI
    print(f"Starting Archimedes Backend on http://localhost:{port}")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False, log_level="debug")
