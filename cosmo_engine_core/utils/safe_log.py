import sys
import logging
import os
import json
import traceback
from datetime import datetime
from typing import Any, Optional

class DeepLogger:
    """
    Structured logger for capturing granular details of the presentation generation process.
    Writes logs to a specific file for later analysis.
    """
    def __init__(self):
        self.log_file: Optional[str] = None
        self.is_enabled = False

    def setup(self, log_path: str):
        self.log_file = log_path
        self.is_enabled = True
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log(f"--- DEEP LOGGING STARTED AT {datetime.now()} ---")

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        if self.is_enabled and self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass
        
        # Also print to console safely
        safe_print(log_entry)

    def log_api_call(self, provider: str, url: str, method: str = "GET", headers: Any = None, payload: Any = None):
        # Sanitize headers
        sanitized_headers = {}
        if headers:
            if isinstance(headers, dict):
                for k, v in headers.items():
                    if k.lower() in ["authorization", "api-key", "x-api-key"]:
                        sanitized_headers[k] = "REDACTED"
                    else:
                        sanitized_headers[k] = v
            else:
                sanitized_headers = "NON-DICT HEADERS"

        msg = f"API CALL [{provider}] {method} {url}\nHeaders: {json.dumps(sanitized_headers)}\nPayload: {json.dumps(payload)}"
        self.log(msg, "DEBUG")

    def log_api_response(self, provider: str, status: int, body: Any):
        msg = f"API RESPONSE [{provider}] Status: {status}\nBody: {json.dumps(body) if isinstance(body, (dict, list)) else body}"
        self.log(msg, "DEBUG")

    def log_error(self, message: str, exception: Optional[Exception] = None):
        error_msg = f"ERROR: {message}"
        if exception:
            error_msg += f"\nException: {str(exception)}\nTraceback:\n{traceback.format_exc()}"
        self.log(error_msg, "ERROR")

# Singleton instance
DEEP_LOGGER = DeepLogger()

def safe_print(message: str, flush: bool = True):
    """
    Prints a message to the console safely, handling UnicodeEncodeErrors on Windows.
    """
    try:
        print(message, flush=flush)
    except UnicodeEncodeError:
        try:
            # Fallback to ASCII with backslashreplace for characters that can't be encoded in the console's encoding
            encoded_msg = message.encode(sys.stdout.encoding, errors='backslashreplace').decode(sys.stdout.encoding)
            print(encoded_msg, flush=flush)
        except Exception:
            # Last resort: just print a generic message or try to strip all non-ascii
            try:
                print(message.encode('ascii', errors='ignore').decode('ascii'), flush=flush)
            except Exception:
                pass

def setup_safe_logging():
    """
    Configures the standard logging module to be more resilient or use safe_print for stream handlers.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
