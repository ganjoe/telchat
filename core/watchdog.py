from __future__ import annotations
from core.registry import AgentRegistry
from typing import Optional, Callable
import time
import threading


class ConnectionWatchdog:
    def __init__(self, registry: AgentRegistry, timeout_seconds: float = 60.0,
                 check_interval: float = 10.0,
                 on_timeout: Optional[Callable[[str], None]] = None):
        """
        F-SYS-020: Monitor agent connections.
        on_timeout is called with the alias of the timed-out agent.
        """
        self.registry = registry
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval
        self.on_timeout = on_timeout
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the watchdog in a background thread."""
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="TelChatWatchdog")
        self._thread.start()

    def stop(self) -> None:
        """Stop the watchdog."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run(self) -> None:
        """Main watchdog loop."""
        while self._running:
            time.sleep(self.check_interval)
            now = time.time()
            # Iterate over connected agents only
            for alias in self.registry.get_connected_agents():
                metadata = self.registry.agents.get(alias)
                if metadata and metadata.last_seen:
                    if (now - metadata.last_seen) > self.timeout_seconds:
                        # Agent timed out
                        self.registry.disconnect(alias)
                        if self.on_timeout:
                            try:
                                self.on_timeout(alias)
                            except Exception as e:
                                print(f"Error in watchdog timeout callback for {alias}: {e}")
