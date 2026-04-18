from __future__ import annotations
from core.message import Message, MessageType
from core.registry import AgentRegistry
from core.router import MessageRouter
from core.watchdog import ConnectionWatchdog
from log.logger import MessageLogger
from ux.cli_parser import CLIParser
import socket
import threading
from typing import Optional, Dict


class TelChatServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999,
                 config_path: str = "config/agents.json"):
        """
        F-SYS-010: Central TCP Hub.
        """
        self.host = host
        self.port = port
        self.registry = AgentRegistry(config_path)
        self.logger = MessageLogger()
        self.router = MessageRouter(self.registry, self.logger)
        self.watchdog = ConnectionWatchdog(
            self.registry, on_timeout=self.router.handle_timeout
        )
        self.server_socket: Optional[socket.socket] = None
        self.client_connections: Dict[str, socket.socket] = {}

    def start(self) -> None:
        """Start TCP server and begin accepting connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        
        self.watchdog.start()
        
        print(f"TelChat server listening on {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address), 
                    daemon=True,
                    name=f"Handler-{address}"
                )
                thread.start()
        except KeyboardInterrupt:
            print("\nStopping server...")
        finally:
            self.watchdog.stop()
            if self.server_socket:
                self.server_socket.close()

    def _handle_client(self, client_socket: socket.socket, address: tuple) -> None:
        """
        Handle a single client connection.
        First message MUST be a registration message.
        """
        alias: Optional[str] = None
        try:
            # Step 1: Wait for registration (Loop until success or disconnect)
            while True:
                raw = self._receive_line(client_socket)
                if not raw:
                    return

                if raw.strip().lower() == "quit":
                    return

                try:
                    msg = Message.from_json(raw)
                    if msg.msg_type == MessageType.REGISTRATION:
                        alias = msg.data.get("alias", "")
                        if self.registry.register_connection(alias):
                            break # Success!
                        else:
                            available = ", ".join(self.registry.agents.keys())
                            self.send_error_feedback(client_socket, f"Alias '{alias}' bereits vergeben.", available)
                    else:
                        self._send(client_socket, "Fehler: Erste Nachricht muss eine Registrierung sein.")
                except ValueError as e:
                    # Fallback für Humans (Telnet): Sie tippen nur ihren Alias (z.B. "human" oder "stm")
                    raw_alias = raw.strip()
                    available = ", ".join(self.registry.agents.keys())
                    agent_meta = self.registry.agents.get(raw_alias)
                    if agent_meta and agent_meta.is_human:
                        if self.registry.register_connection(raw_alias):
                            alias = raw_alias
                            self._send(client_socket, f"Erfolgreich als Human angemeldet: {alias}")
                            # Erzeuge eine Dummy-Registration Message für das Logfile
                            import time
                            msg = Message(sender=alias, recipient="router", msg_type=MessageType.REGISTRATION, 
                                          timestamp=time.time(), data={"alias": alias}, byte_count=0)
                            break # Success!
                        else:
                            self.send_error_feedback(client_socket, f"Alias '{raw_alias}' bereits verbunden.", available)
                    else:
                        self.send_error_feedback(client_socket, f"'{raw_alias}' ist kein gueltiger Human-Alias.", available)

            # Step 3: Setup connection
            self.client_connections[alias] = client_socket
            self.router.register_send_function(
                alias, 
                lambda data, s=client_socket: self._send(s, data)
            )
            self.logger.log(msg, direction="RECV")

            # Step 4: Main receive loop
            while True:
                raw = self._receive_line(client_socket)
                if raw is None:
                    break
                
                if not raw.strip():
                    continue
                    
                if raw.strip().lower() == "quit":
                    self._send(client_socket, "Verbindung beendet. Goodbye!")
                    break

                # Handle Human CLI syntax (@recipient text)
                agent_meta = self.registry.agents.get(alias)
                if agent_meta and agent_meta.is_human:
                    stripped = raw.strip()
                    if stripped.startswith("@"):
                        parsed = CLIParser.parse(stripped, sender=alias)
                        if parsed:
                            self.registry.update_last_seen(alias)
                            self.router.route(parsed)
                        else:
                            self._send(client_socket, f"Fehler: Ungueltiges Routing. Format: @empfaenger text. Echo: {stripped}")
                        continue
                    elif stripped.startswith("{"):
                        # Wahrscheinlich JSON, an den normalen JSON-Parser weitergeben
                        pass
                    else:
                        # Ungültige Roheingabe von Human -> Fehler + Echo
                        self._send(client_socket, f"Fehler: Befehle muessen mit '@' beginnen (z.B. '@pta status'). Echo: {stripped}")
                        continue

                # Handle normal JSON messages
                try:
                    msg = Message.from_json(raw)
                    if msg.sender != alias:
                        # Security: Prevent identity spoofing
                        continue
                    self.registry.update_last_seen(alias)
                    self.logger.log(msg, direction="RECV")
                    self.router.route(msg)
                except ValueError as e:
                    if agent_meta and agent_meta.is_human:
                        self._send(client_socket, f"Fehler: Ungueltiges JSON. Echo: {raw.strip()}")
                    # Ignore malformed messages within a session but log the reason
                    print(f"Dropping malformed message from {alias}: {e}")
                    continue

        except (socket.error, ConnectionError):
            pass
        finally:
            if alias:
                self.registry.disconnect(alias)
                self.router.unregister_send_function(alias)
                self.client_connections.pop(alias, None)
            client_socket.close()

    def send_error_feedback(self, sock: socket.socket, message: str, available_aliases: str) -> None:
        """Helper to send a formatted error message with a list of available aliases."""
        self._send(sock, f"FEHLER: {message}")
        self._send(sock, f"VERFUEGBARE ALIASE: {available_aliases}")
        self._send(sock, "--------------------------------------------------")

    def _receive_line(self, sock: socket.socket) -> Optional[str]:
        """Read one newline-terminated line from socket."""
        buffer = b""
        while True:
            try:
                chunk = sock.recv(1)
                if not chunk:
                    return None
                if chunk == b"\n":
                    break
                buffer += chunk
            except socket.error:
                return None
        return buffer.decode("utf-8")

    def _send(self, sock: socket.socket, data: str) -> None:
        """Send a newline-terminated string to a socket."""
        try:
            sock.sendall((data + "\n").encode("utf-8"))
        except (socket.error, ConnectionError):
            pass
