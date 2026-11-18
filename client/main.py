"""
Client application entry point.
Run with: python -m client.main
"""

import argparse
import sys
from client.config import ClientConfig
from gui.chat_window import ConnectApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Connect — Real-Time Chat Client")
    parser.add_argument("--config", type=str, default="client_config.json", help="Path to client config file")
    parser.add_argument("--host", type=str, default=None, help="Server host to connect to")
    parser.add_argument("--port", type=int, default=None, help="Server port to connect to")
    args = parser.parse_args()

    # Load and optionally override config
    config = ClientConfig.load(args.config)
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    config.save()

    app = ConnectApp(config_path=args.config)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
