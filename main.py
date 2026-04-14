#!/usr/bin/env python3
"""TelChat – Central TCP Message Hub"""

from net.tcp_server import TelChatServer
import sys
import os


def main():
    # Load configuration from environment variables or use defaults
    config_path = os.environ.get("TELCHAT_CONFIG", "config/agents.json")
    host = os.environ.get("TELCHAT_HOST", "0.0.0.0")
    
    try:
        port = int(os.environ.get("TELCHAT_PORT", "9999"))
    except ValueError:
        print("Error: TELCHAT_PORT must be an integer.", file=sys.stderr)
        sys.exit(1)

    # Initialize and start server
    try:
        server = TelChatServer(host=host, port=port, config_path=config_path)
        server.start()
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"System Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
