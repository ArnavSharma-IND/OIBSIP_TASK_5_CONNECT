"""
Server executable entry point.
Run with: python -m server.main
"""

import argparse
import signal
import sys
from utils.logger import get_logger
from server.config import load_server_config
from server.server import TCPServer

logger = get_logger("ServerMain")


def main() -> None:
    parser = argparse.ArgumentParser(description="Connect — Real-Time Chat Server")
    parser.add_argument("--host", type=str, default=None, help="Host address to bind to (e.g. 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (e.g. 5000)")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database file")
    parser.add_argument("--config", type=str, default=None, help="Path to JSON configuration file")
    args = parser.parse_args()

    config = load_server_config(args.config)
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.db:
        config.db_path = args.db

    server = TCPServer(config)

    def handle_signal(sig, frame):
        logger.info(f"Signal {sig} received. Shutting down server...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    server.start(block=True)


if __name__ == "__main__":
    main()
