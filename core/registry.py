from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import time
import os


@dataclass
class AgentMetadata:
    alias: str
    is_human: bool
    description: str
    connection_time: Optional[float] = None
    last_seen: Optional[float] = None
    is_connected: bool = False
    timeout_reported: bool = False


class AgentRegistry:
    def __init__(self, config_path: str):
        """
        F-CFG-140: Load allowed aliases from config file.
        """
        self.agents: Dict[str, AgentMetadata] = {}
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in config file: {config_path}")

        if "agents" not in config:
            raise ValueError("Config file missing 'agents' key")

        for entry in config["agents"]:
            alias = entry["alias"]
            if alias in self.agents:
                raise ValueError(f"Duplicate alias in config: {alias}")

            self.agents[alias] = AgentMetadata(
                alias=alias,
                is_human=entry.get("is_human", False),
                description=entry.get("description", "")
            )

    def is_valid_alias(self, alias: str) -> bool:
        """Returns True if alias exists in config."""
        return alias in self.agents

    def register_connection(self, alias: str) -> bool:
        """
        F-REG-070: Mark agent as connected.
        Returns True if successful, False if alias is unknown.
        """
        if not self.is_valid_alias(alias):
            return False

        agent = self.agents[alias]
        agent.connection_time = time.time()
        agent.last_seen = time.time()
        agent.is_connected = True
        return True

    def disconnect(self, alias: str) -> None:
        """Mark agent as disconnected."""
        if alias in self.agents:
            self.agents[alias].is_connected = False
            self.agents[alias].connection_time = None

    def update_last_seen(self, alias: str) -> None:
        """Update last_seen timestamp for watchdog and reset warning state."""
        if alias in self.agents:
            self.agents[alias].last_seen = time.time()
            self.agents[alias].timeout_reported = False

    def get_connected_humans(self) -> List[str]:
        """Returns list of aliases where is_human=True AND is_connected=True."""
        return [a for a, m in self.agents.items() if m.is_human and m.is_connected]

    def get_connected_agents(self) -> List[str]:
        """Returns list of all connected aliases."""
        return [a for a, m in self.agents.items() if m.is_connected]
