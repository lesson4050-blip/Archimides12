import sys
import logging

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
    (Optional enhancement)
    """
    pass
