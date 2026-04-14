from __future__ import annotations
from core.message import Message
import os
from datetime import datetime


class MessageLogger:
    def __init__(self, log_dir: str = "logs"):
        """
        F-LOG-130: Initialize logger with a log directory.
        """
        self.log_dir = log_dir
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            # Fallback to current directory if logs cannot be created
            print(f"Warning: Could not create log directory {log_dir}: {e}. Logging to current directory.")
            self.log_dir = "."

        filename = f"telchat_{datetime.now().strftime('%Y%m%d')}.log"
        self.log_path = os.path.join(self.log_dir, filename)

    def log(self, message: Message, direction: str = "ROUTE") -> None:
        """
        Append one line per message to the log file.
        direction is one of: "RECV", "ROUTE", "SEND", "DROP"
        """
        try:
            log_line = (
                f"[{datetime.now().isoformat()}] [{direction}] "
                f"{message.sender} -> {message.recipient} "
                f"[{message.msg_type.value}] "
                f"{message.to_json()}\n"
            )
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except OSError as e:
            # Prevent server crash if logging fails (e.g. disk full)
            import sys
            print(f"Error writing to log file {self.log_path}: {e}", file=sys.stderr)
