from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any
import json
import time


class MessageType(Enum):
    REGISTRATION = "registration"
    DATA = "data"
    ERROR = "error"
    ACK = "ack"


@dataclass(frozen=True)
class Message:
    """
    F-COM-030: Immutable message object.
    F-COM-050: Contains byte_count validation.
    """
    sender: str
    recipient: str
    msg_type: MessageType
    timestamp: float
    data: Dict[str, Any]
    byte_count: int

    def to_json(self) -> str:
        """Serialize to JSON string for TCP transmission."""
        return json.dumps({
            "from": self.sender,
            "to": self.recipient,
            "msg_type": self.msg_type.value,
            "timestamp": self.timestamp,
            "byte_count": self.byte_count,
            "data": self.data
        })

    @staticmethod
    def from_json(raw: str) -> Message:
        """
        Deserialize JSON string into Message object.
        Raises ValueError if JSON is invalid or fields are missing.
        """
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON")

        required_keys = ["from", "to", "msg_type", "timestamp", "byte_count", "data"]
        for key in required_keys:
            if key not in obj:
                raise ValueError(f"Missing field: {key}")

        try:
            m_type = MessageType(obj["msg_type"])
        except ValueError:
            raise ValueError(f"Unknown msg_type: {obj['msg_type']}")

        # F-COM-050: Verify byte_count matches serialized data
        data_json = json.dumps(obj["data"])
        actual_bytes = len(data_json.encode("utf-8"))
        if obj["byte_count"] != actual_bytes:
            raise ValueError(f"byte_count mismatch: expected {obj['byte_count']}, got {actual_bytes}")

        return Message(
            sender=obj["from"],
            recipient=obj["to"],
            msg_type=m_type,
            timestamp=obj["timestamp"],
            data=obj["data"],
            byte_count=obj["byte_count"]
        )

    @staticmethod
    def create(sender: str, recipient: str, msg_type: MessageType, data: Dict[str, Any]) -> Message:
        """
        Factory method. Automatically sets timestamp and calculates byte_count.
        """
        ts = time.time()
        byte_count = len(json.dumps(data).encode("utf-8"))
        return Message(
            sender=sender,
            recipient=recipient,
            msg_type=msg_type,
            timestamp=ts,
            data=data,
            byte_count=byte_count
        )
