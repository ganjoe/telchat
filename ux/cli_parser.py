from __future__ import annotations
from core.message import Message, MessageType
from typing import Optional


class CLIParser:
    """
    F-UX-090: Parses human text input into Message objects.
    Input format: "@<recipient> <text>"
    """

    @staticmethod
    def parse(raw_input: str, sender: str = "human") -> Optional[Message]:
        """
        Parse a raw CLI string into a Message.
        Returns None if input is invalid.
        """
        raw_input = raw_input.strip()
        if not raw_input.startswith("@"):
            return None

        # Split on first space to separate @recipient and text
        parts = raw_input.split(" ", 1)
        recipient = parts[0][1:]  # remove the "@"

        if not recipient:
            return None

        text = parts[1] if len(parts) > 1 else ""
        data = {"text": text}

        # Use Message.create factory (sets timestamp and byte_count automatically)
        return Message.create(
            sender=sender,
            recipient=recipient,
            msg_type=MessageType.DATA,
            data=data
        )
