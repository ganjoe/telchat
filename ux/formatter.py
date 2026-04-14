from __future__ import annotations
from typing import Dict, Any
from datetime import datetime
import json


class HumanFormatter:
    @staticmethod
    def format_timestamp(ts: float) -> str:
        """
        F-UX-100: Convert Unix timestamp to human-readable local time.
        Output format: "2026-04-14 22:30:00"
        """
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def dict_to_table(data: Dict[str, Any]) -> str:
        """
        F-UX-080: Convert a flat dictionary to a text table.
        Uses box-drawing characters for premium Look & Feel.
        """
        if not data:
            return "(empty data)"

        # Prepare strings and calculate widths
        rows = []
        for k, v in data.items():
            val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            rows.append((str(k), val_str))

        key_width = max(max(len(k) for k, v in rows), 3)  # min 3 for "Key"
        val_width = max(max(len(v) for k, v in rows), 5)  # min 5 for "Value"

        # Table Components
        top = f"┌{'─' * (key_width + 2)}┬{'─' * (val_width + 2)}┐"
        head = f"│ {'Key':<{key_width}} │ {'Value':<{val_width}} │"
        mid = f"├{'─' * (key_width + 2)}┼{'─' * (val_width + 2)}┤"
        bot = f"└{'─' * (key_width + 2)}┴{'─' * (val_width + 2)}┘"

        lines = [top, head, mid]
        for k, v in rows:
            lines.append(f"│ {k:<{key_width}} │ {v:<{val_width}} │")
        lines.append(bot)

        return "\n".join(lines)

    @staticmethod
    def format_message_for_human(sender: str, timestamp: float, data: Dict[str, Any]) -> str:
        """
        Combines timestamp and table formatting.
        """
        formatted_time = HumanFormatter.format_timestamp(timestamp)
        header = f"── {sender} @ {formatted_time} ──"
        table = HumanFormatter.dict_to_table(data)
        return f"{header}\n{table}"
