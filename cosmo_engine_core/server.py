import uvicorn
import argparse
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI server")
    parser.add_argument(
        "--port", type=int, required=True, help="Port number to run the server on"
    )
    parser.add_argument(
        "--reload", type=str, default="false", help="Reload the server on code changes"
    )
    args = parser.parse_args()
    reload = args.reload == "true"
    
    import logging
    import os
    from utils.get_env import get_app_data_directory_env

    app_data_dir = get_app_data_directory_env() or "data"
    log_dir = os.path.join(app_data_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    server_log_path = os.path.join(log_dir, "server.log")

    # Basic logging config for the server process itself
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(server_log_path, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    # Redirect stdout and stderr to the log file to capture all prints and tracebacks
    log_file = open(server_log_path, "a", encoding="utf-8")
    import sys
    sys.stdout = log_file
    sys.stderr = log_file

    print(f"\n--- SERVER STARTUP AT {datetime.now()} ---")
    print(f"Server logs and prints will be written to {server_log_path}")

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=args.port,
        log_level="info",
        reload=reload,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(levelname)s] %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": server_log_path,
                    "encoding": "utf-8",
                },
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["file", "console"],
            },
        }
    )
