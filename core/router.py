from __future__ import annotations
from core.message import Message, MessageType
from core.registry import AgentRegistry
from log.logger import MessageLogger
from ux.formatter import HumanFormatter
from typing import Dict, Callable


class MessageRouter:
    def __init__(self, registry: AgentRegistry, logger: MessageLogger):
        """
        F-COM-040: Central routing logic.
        """
        self.registry = registry
        self.logger = logger
        self.send_functions: Dict[str, Callable[[str], None]] = {}

    def register_send_function(self, alias: str, send_fn: Callable[[str], None]) -> None:
        """Register the TCP send function for a specific alias."""
        self.send_functions[alias] = send_fn

    def unregister_send_function(self, alias: str) -> None:
        """Remove send function when agent disconnects."""
        self.send_functions.pop(alias, None)

    def route(self, message: Message) -> None:
        """
        F-COM-040: Route a message based on its 'to' field.
        """
        self.logger.log(message, direction="ROUTE")

        # F-COM-060: ACK messages are forwarded as raw JSON without formatting
        if message.msg_type == MessageType.ACK:
            self._send_raw(message.recipient, message.to_json(), message)
            return

        # Check if recipient is human for broadcast logic
        recipient_metadata = self.registry.agents.get(message.recipient)
        
        # F-SYS-120: If recipient is marked as human, broadcast to ALL connected humans
        if recipient_metadata and recipient_metadata.is_human:
            humans = self.registry.get_connected_humans()
            if not humans:
                 self.logger.log(message, direction="DROP")
                 return
                 
            formatted = HumanFormatter.format_message_for_human(
                message.sender, message.timestamp, message.data
            )
            for human_alias in humans:
                if human_alias in self.send_functions:
                    self.send_functions[human_alias](formatted)
            
            self.logger.log(message, direction="SEND")
            return

        # Standard agent-to-agent routing
        self._send_raw(message.recipient, message.to_json(), message)

    def handle_timeout(self, alias: str) -> None:
        """
        F-SYS-020 + F-ERR-110: Called by watchdog when an agent times out.
        Emit a warning instead of disconnecting.
        """
        error_msg = Message.create(
            sender="system", 
            recipient="human",
            msg_type=MessageType.ERROR,
            data={"error": f"Agent '{alias}' hat seit 60 Sekunden keinen Heartbeat gesendet (möglicherweise blockiert/abgestürzt)."}
        )
        self.route(error_msg)

    def _send_raw(self, recipient: str, payload: str, original_msg: Message) -> None:
        """Helper to send raw data to an agent or report error."""
        if recipient in self.send_functions:
            self.send_functions[recipient](payload)
            self.logger.log(original_msg, direction="SEND")
        else:
            # F-ERR-110: Feedback if agent is unknown or not connected
            self.logger.log(original_msg, direction="DROP")
            if original_msg.sender != "system": # Avoid infinite error loops
                self._send_error(f"Recipient agent '{recipient}' is not connected", original_msg.sender)

    def _send_error(self, error_text: str, recipient: str) -> None:
        """Internal helper for system errors."""
        error_msg = Message.create(
            sender="system", 
            recipient=recipient,
            msg_type=MessageType.ERROR,
            data={"error": error_text}
        )
        self.route(error_msg)
